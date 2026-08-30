from __future__ import print_function

import ast
import builtins as py_builtins
import importlib
import importlib.util
import inspect
import json
import keyword
import os
import re
import shutil
import subprocess
import sys

import wx
import wx.stc as stc


SyntaxErrorMarker = 22
RuffErrorMarker = 23


def infer_syntax_from_filename(filename, default='none'):
    if not filename:
        return default

    ext = os.path.splitext(str(filename))[1].lower()

    if ext in ('.py', '.pyw', '.pyi'):
        return 'python'
    if ext in ('.c', '.h'):
        return 'c'
    if ext in ('.cc', '.cp', '.cpp', '.cxx', '.hh', '.hpp', '.hxx'):
        return 'c++'
    if ext in ('.f', '.for', '.f77', '.ftn'):
        return 'f77'
    if ext in ('.f90', '.f95', '.f03', '.f08'):
        return 'fortran'

    return default


class PythonCompletionSyntaxMixin(object):
    def __init__(self, syntax='python'):
        self._syntax = syntax
        self._checking_mode = 'syntax_minimum'
        self._external_namespace = {}
        self._external_namespace_provider = None
        self._ac_min_prefix = 2
        self._syntax_check_delay_ms = 400
        self._syntax_check_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnSyntaxCheckTimer, self._syntax_check_timer)
        self._import_alias_cache_key = None
        self._import_alias_cache = {}
        self._ruff_checked = False
        self._ruff_available = False

    def get_checking_mode(self):
        return self._checking_mode

    def set_external_namespace(self, namespace):
        if namespace is None:
            self._external_namespace = {}
        else:
            self._external_namespace = dict(namespace)

    def set_external_namespace_provider(self, provider):
        self._external_namespace_provider = provider

    def get_external_namespace(self):
        return self._get_external_namespace()

    def _get_external_namespace(self):
        ns = dict(self._external_namespace)
        provider = self._external_namespace_provider

        if callable(provider):
            provided = None
            try:
                provided = provider(self)
            except TypeError:
                try:
                    provided = provider()
                except Exception:
                    provided = None
            except Exception:
                provided = None
            if isinstance(provided, dict):
                ns.update(provided)
        return ns

    def _get_completion_namespace(self):
        ns = self._get_runtime_namespace()
        ns.update(self._get_external_namespace())
        return ns

    def _get_dynamic_builtin_names(self):
        names = set(dir(py_builtins))
        names.update(self._get_external_namespace().keys())
        return names

    def _is_completion_enabled(self):
        return self._checking_mode != 'off'

    def _is_syntax_check_enabled(self):
        return self._checking_mode in ('syntax_minimum', 'syntax_modest', 'syntax_noisy')

    def set_checking_mode(self, mode):
        valid_modes = ('off', 'completion_only', 'syntax_minimum',
                       'syntax_modest', 'syntax_noisy')
        if mode not in valid_modes:
            mode = 'syntax_minimum'
        self._checking_mode = mode

        if not self._is_syntax_check_enabled():
            if hasattr(self, '_syntax_check_timer'):
                self._syntax_check_timer.Stop()
            self._clear_syntax_diagnostics()
        if self._syntax == 'python' and self._is_syntax_check_enabled():
            self._schedule_syntax_check()

    def get_completion_syntax_check_enabled(self):
        return self._is_syntax_check_enabled()

    def set_completion_syntax_check_enabled(self, value):
        if value:
            self.set_checking_mode('syntax_minimum')
        else:
            self.set_checking_mode('off')

    def _schedule_syntax_check(self, delay=None):
        if not self._is_syntax_check_enabled():
            return
        if not hasattr(self, '_syntax_check_timer'):
            return
        if delay is None:
            delay = self._syntax_check_delay_ms
        try:
            self._syntax_check_timer.StartOnce(delay)
        except AttributeError:
            self._syntax_check_timer.Start(delay, True)

    def _clear_syntax_diagnostics(self):
        self.MarkerDeleteAll(SyntaxErrorMarker)
        self.MarkerDeleteAll(RuffErrorMarker)
        self.AnnotationClearAll()

    def _check_ruff_available(self):
        if self._ruff_checked:
            return self._ruff_available
        self._ruff_checked = True
        self._ruff_available = (shutil.which('ruff') is not None or
                                importlib.util.find_spec('ruff') is not None)
        return self._ruff_available

    def _build_ruff_cmd(self, select_codes):
        base_args = ['check', '--select', select_codes, '--output-format', 'json']
        if shutil.which('ruff') is not None:
            return ['ruff'] + base_args
        if importlib.util.find_spec('ruff') is not None:
            return [sys.executable, '-m', 'ruff'] + base_args
        return None

    def _ruff_select_codes_for_mode(self):
        if self._checking_mode == 'syntax_minimum':
            return 'F821,F823,F822'
        if self._checking_mode == 'syntax_modest':
            return 'F821,F823,F822,F811,E722'
        if self._checking_mode == 'syntax_noisy':
            return 'F821,F823,F822,F811,E722,F401,F841,B006,B008'
        return ''

    def _run_ruff_check(self):
        if not self._check_ruff_available():
            return []

        select_codes = self._ruff_select_codes_for_mode()
        if not select_codes:
            return []

        cmd = self._build_ruff_cmd(select_codes)

        if cmd is None:
            return []

        filename = self.doc_name if self.doc_name else 'untitled.py'
        if not filename.endswith('.py'):
            filename = filename + '.py'
        cmd = cmd + ['--stdin-filename', filename, '-']

        try:
            proc = subprocess.run(cmd,
                                  input=self.GetText(),
                                  capture_output=True,
                                  text=True,
                                  check=False)
        except Exception:
            return []

        if proc.returncode not in (0, 1):
            return []

        txt = proc.stdout.strip()
        if not txt:
            return []

        try:
            data = json.loads(txt)
        except Exception:
            return []

        out = []
        for item in data:
            loc = item.get('location', {})
            row = loc.get('row', 1)
            msg = item.get('message', 'Undefined name')
            code = item.get('code', 'F821')
            if code in ('F821', 'F822', 'F823'):
                name = self._extract_ruff_name(msg)
                if name and name in self._get_dynamic_builtin_names():
                    continue
            out.append((max(row - 1, 0), code + ': ' + msg))
        return out

    def _extract_ruff_name(self, msg):
        m = re.search(r"[`'\"]([A-Za-z_][A-Za-z0-9_]*)[`'\"]", msg)
        if m:
            return m.group(1)
        m = re.search(r"Undefined name\s+([A-Za-z_][A-Za-z0-9_]*)", msg)
        if m:
            return m.group(1)
        return ''

    def _collect_completion_candidates(self):
        candidates = set(keyword.kwlist)
        candidates.update(self._get_dynamic_builtin_names())
        candidates.update(self._get_completion_namespace().keys())
        candidates.update(self._get_import_alias_map().keys())
        candidates.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", self.GetText()))
        return candidates

    def _get_import_alias_map(self):
        txt = self.GetText()
        key = (len(txt), hash(txt))
        if key == self._import_alias_cache_key:
            return self._import_alias_cache

        alias_map = {}
        try:
            tree = ast.parse(txt)
        except SyntaxError:
            alias_map = self._parse_import_aliases_regex(txt)
            self._import_alias_cache_key = key
            self._import_alias_cache = alias_map
            return alias_map

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        alias_map[alias.asname] = alias.name
                    else:
                        alias_map[alias.name.split('.')[0]] = alias.name.split('.')[0]
            elif isinstance(node, ast.ImportFrom):
                if node.level != 0 or node.module is None:
                    continue
                for alias in node.names:
                    if alias.name == '*':
                        continue
                    bind_name = alias.asname or alias.name
                    alias_map[bind_name] = node.module + '.' + alias.name

        self._import_alias_cache_key = key
        self._import_alias_cache = alias_map
        return alias_map

    def _parse_import_aliases_regex(self, txt):
        alias_map = {}
        for raw in txt.splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue

            m = re.match(r'^import\s+(.+)$', line)
            if m:
                chunks = [x.strip() for x in m.group(1).split(',')]
                for chunk in chunks:
                    if not chunk:
                        continue
                    parts = [x.strip() for x in chunk.split(' as ', 1)]
                    if len(parts) == 2:
                        full_name, as_name = parts
                        if as_name:
                            alias_map[as_name] = full_name
                    else:
                        root = parts[0].split('.')[0]
                        if root:
                            alias_map[root] = root
                continue

            m = re.match(r'^from\s+([A-Za-z_][A-Za-z0-9_\.]*)\s+import\s+(.+)$', line)
            if m:
                mod = m.group(1)
                names = [x.strip() for x in m.group(2).split(',')]
                for chunk in names:
                    if not chunk or chunk == '*':
                        continue
                    parts = [x.strip() for x in chunk.split(' as ', 1)]
                    src_name = parts[0]
                    bind_name = parts[1] if len(parts) == 2 and parts[1] else src_name
                    if bind_name and src_name:
                        alias_map[bind_name] = mod + '.' + src_name

        return alias_map

    def _import_object_from_path(self, path):
        if not path:
            return None

        try:
            return importlib.import_module(path)
        except Exception:
            pass

        parts = path.split('.')
        for i in range(len(parts)-1, 0, -1):
            mod_name = '.'.join(parts[:i])
            attrs = parts[i:]
            try:
                obj = importlib.import_module(mod_name)
            except Exception:
                continue

            ok = True
            for attr in attrs:
                try:
                    obj = getattr(obj, attr)
                except Exception:
                    ok = False
                    break
            if ok:
                return obj
        return None

    def _get_runtime_namespace(self):
        ns = {}
        app = wx.GetApp()
        if app is None or not hasattr(app, 'TopWindow'):
            return ns
        top = app.TopWindow
        try:
            interp = top.shell.interp
            if hasattr(interp, 'locals') and isinstance(interp.locals, dict):
                ns.update(interp.locals)
            if hasattr(interp, 'globals') and isinstance(interp.globals, dict):
                ns.update(interp.globals)
        except Exception:
            pass
        return ns

    def _resolve_dotted_name(self, dotted):
        if not dotted:
            return None
        extra_ns = self._get_external_namespace()
        if dotted in extra_ns:
            return extra_ns[dotted]
        ns = self._get_runtime_namespace()
        if dotted in ns:
            return ns[dotted]
        if dotted in sys.modules:
            return sys.modules[dotted]

        parts = dotted.split('.')
        if not parts:
            return None

        obj = extra_ns.get(parts[0], None)
        if obj is None:
            obj = ns.get(parts[0], None)
        if obj is None:
            obj = sys.modules.get(parts[0], None)
        if obj is None:
            alias_map = self._get_import_alias_map()
            root = alias_map.get(parts[0], '')
            if root:
                obj = self._import_object_from_path(root)
        if obj is None:
            return None

        for attr in parts[1:]:
            if isinstance(obj, dict):
                if attr in obj:
                    obj = obj[attr]
                    continue
                return None
            try:
                obj = getattr(obj, attr)
            except Exception:
                return None
        return obj

    def _collect_member_candidates(self, obj, prefix):
        if obj is None:
            return []
        prefix_l = prefix.lower()
        out = []
        try:
            if isinstance(obj, dict):
                for name in obj.keys():
                    if str(name).lower().startswith(prefix_l):
                        out.append(str(name))
                return sorted(set(out))
            for name in dir(obj):
                if name.lower().startswith(prefix_l):
                    out.append(name)
        except Exception:
            return []
        return sorted(set(out))

    def _show_member_autocomplete(self):
        if not self._is_completion_enabled():
            return
        if self._syntax != 'python':
            return
        pos = self.GetCurrentPos()
        line = self.GetCurLine()[0][:self.GetColumn(pos)]
        m = re.search(r"([A-Za-z_][A-Za-z0-9_\.]*)\.([A-Za-z0-9_]*)$", line)
        if m is None:
            return
        target = m.group(1)
        prefix = m.group(2)
        obj = self._resolve_dotted_name(target)
        names = self._collect_member_candidates(obj, prefix)
        if not names:
            return
        if len(names) > 200:
            names = names[:200]
        self.AutoCompSetIgnoreCase(True)
        self.AutoCompSetAutoHide(True)
        self.AutoCompSetDropRestOfWord(False)
        self.AutoCompShow(len(prefix), " ".join(names))

    def _extract_callable_token(self, txt):
        txt = txt.rstrip()
        m = re.search(r"([A-Za-z_][A-Za-z0-9_\.]*)$", txt)
        if m is None:
            return ''
        return m.group(1)

    def _format_calltip(self, token, obj):
        sig_txt = '(...)'
        try:
            sig_txt = str(inspect.signature(obj))
        except Exception:
            try:
                argspec = inspect.getfullargspec(obj)
                sig_txt = inspect.formatargspec(*argspec)
            except Exception:
                pass
        doc = inspect.getdoc(obj) or ''
        if doc:
            doc = doc.splitlines()[0]
            if len(doc) > 96:
                doc = doc[:93] + '...'
            return token + sig_txt + "\n" + doc
        return token + sig_txt

    def _show_calltip(self):
        if not self._is_completion_enabled():
            return
        if self._syntax != 'python':
            return
        pos = self.GetCurrentPos()
        if pos <= 0:
            return
        line = self.GetCurLine()[0][:self.GetColumn(pos)]
        token = self._extract_callable_token(line)
        if not token:
            return
        obj = self._resolve_dotted_name(token)
        if obj is None:
            return
        if not callable(obj):
            return
        self.CallTipShow(pos, self._format_calltip(token, obj))

    def _show_autocomplete(self, force=False):
        if not self._is_completion_enabled():
            return
        if self._syntax != 'python':
            return
        pos = self.GetCurrentPos()
        start = self.WordStartPosition(pos, True)
        prefix = self.GetTextRange(start, pos)
        if not force and len(prefix) < self._ac_min_prefix:
            return

        prefix_l = prefix.lower()
        names = self._collect_completion_candidates()
        matches = [x for x in names if x.lower().startswith(prefix_l)]
        if not matches:
            return

        matches = sorted(matches)
        if len(matches) > 200:
            matches = matches[:200]

        self.AutoCompSetIgnoreCase(True)
        self.AutoCompSetAutoHide(True)
        self.AutoCompSetDropRestOfWord(False)
        self.AutoCompShow(len(prefix), " ".join(matches))

    def _run_python_syntax_check(self):
        self._clear_syntax_diagnostics()
        if not self._is_syntax_check_enabled():
            return
        if self._syntax != 'python':
            return

        try:
            ast.parse(self.GetText())
        except SyntaxError as err:
            line = max((err.lineno or 1) - 1, 0)
            msg = err.msg or 'Syntax error'
            self.MarkerAdd(line, SyntaxErrorMarker)
            self.AnnotationSetText(line, msg)
            return

        ruff_errors = self._run_ruff_check()
        if not ruff_errors:
            return

        line_to_msgs = {}
        for line, msg in ruff_errors:
            self.MarkerAdd(line, RuffErrorMarker)
            if line not in line_to_msgs:
                line_to_msgs[line] = []
            line_to_msgs[line].append(msg)

        for line in line_to_msgs:
            self.AnnotationSetText(line, '\n'.join(line_to_msgs[line]))

    def OnSyntaxCheckTimer(self, evt):
        self._run_python_syntax_check()
        evt.Skip()

    def OnBufferModified(self, evt):
        if not self._is_syntax_check_enabled():
            evt.Skip()
            return
        mtype = evt.GetModificationType()
        if mtype & (stc.STC_MOD_INSERTTEXT | stc.STC_MOD_DELETETEXT):
            self._schedule_syntax_check()
        evt.Skip()

    def OnCharAdded(self, evt):
        if not self._is_completion_enabled():
            evt.Skip()
            return
        if self._syntax != 'python':
            evt.Skip()
            return

        key = evt.GetKey()
        if key > 0:
            try:
                ch = chr(key)
            except ValueError:
                ch = ''
            if ch == '.':
                self._show_member_autocomplete()
            elif ch == '(':
                self._show_calltip()
            elif ch == '_' or ch.isalnum():
                self._show_autocomplete()
        self._schedule_syntax_check()
        evt.Skip()
