import numpy as np


def read_ishotktime(f):
    line = f.readline()
    line = line.rstrip("\r\n")

    a = line.split(' ')
    a = [x for x in a if len(x) != 0]
    return int(a[0]), int(a[1])


def read1055(f):
    '''
    form1055 = '(1x,a10,2a5)'
    '''
    line = f.readline()
    line = line.rstrip("\r\n")

    a = line[1:11]
    b = line[11:16]
    c = line[16:21]
    return a, (b, c)


def read1060(f):
    '''
    form1060=' (1x ,f7.2,10x,i5,11x,i5,1x,a3,1x,i3,1x,i3,1x,a3)'
    '''
    line = f.readline()
    line = line.rstrip("\r\n")

    a = line[1:8]
    b = line[18:23]
    c = line[34:39]
    d = line[40:43]
    e = line[44:47]
    f = line[48:51]
    g = line[52:55]
    return float(a), int(b), int(c), d, int(e), int(f), g


def read1040(f):
    '''
    form1040 = '(1x,4e16.9)'
    '''
    line = f.readline()
    line = line.rstrip("\r\n")
    line = line + ' '*45
    a = line[1:17]
    b = line[17:33]
    c = line[33:49]
    d = line[49:65]

    return a, b, c, d


def read1040f(f):
    a, b, c, d = read1040(f)
    return float(a), float(b), float(c), float(d)


def read1040_array(f, num):
    i = 0
    val = ()
    while(i < num):
        val = val + read1040(f)
        i = i+4
    return [float(x) for x in val[0:num]]


def read_afile(file=None):
    '''
       form1055 = '(1x,a10,2a5)'
       uday = ''
       mfvers = strarr(2)
       ishot = 0l
       ktime1=0l
       jflag=0l
       lflag=jflag
       limloc=0l
       mco2v=0l
       mco2r=0l
       qmflag = ''
       form1060=' (1x ,f7.2,10x,i5,11x,i5,1x,a3,1x,i3,1x,i3,1x,a3)'
       limloc = ''
       on_ioerror,abinary
       readf,2,form=form1055,uday,mfvers
       readf,2,ishot,ktime1
       on_ioerror,null
       readf,2,time
       readf,2,timejj,jflag,lflag,limloc,mco2v,mco2r,qmflag,form=form1060
       form1040 = '(1x,4e16.9)'
       readf,2,form=form1040,tsaisq,rcencm,bcentr,pasmat
       readf,2,form=form1040,cpasma,rout,zout,aout
       readf,2,form=form1040,eout,doutu,doutl,vout
       readf,2,form=form1040,rcurrt,zcurrt,qsta,betat
       readf,2,form=form1040,betap,ali,oleft,oright
       readf,2,form=form1040,otop,obott,qpsib,vertn
       rco2v = fltarr(mco2v)
       dco2v = rco2v
       rco2r = fltarr(mco2r)
       dco2r = rco2r
       readf,2,form=form1040,rco2v
       readf,2,form=form1040,dco2v
       readf,2,form=form1040,rco2r
       readf,2,form=form1040,dco2r
       readf,2,form=form1040,shearb,bpolav,s1,s2
       readf,2,form=form1040,s3,qout,olefs,orighs
       readf,2,form=form1040,otops,sibdry,areao,wplasm
       readf,2,form=form1040,terror,elongm,qqmagx,cdflux
       readf,2,form=form1040,alpha,rttt,psiref,xndnt
       rzseps = fltarr(2,2)
       readf,2,form=form1040,rzseps
       rseps = transpose(rzseps(0,*))
       zseps = transpose(rzseps(1,*))
       readf,2,form=form1040,sepexp,obots,btaxp,btaxv
       readf,2,form=form1040,aaq1,aaq2,aaq3,seplim
       readf,2,form=form1040,rmagx,zmagx,simagx,taumhd
       readf,2,form=form1040,betapd,betatd,wplasmd,fluxx
       readf,2,form=form1040,vloopt,taudia,qmerci,tavem
       ; The next bunch of things needs to know nsilop,magpri,nfcoil,nesum
       ; These guys are in parameter statements in eparmdn.for
       nfcoil = 15
       nsilop = 26
       magpri = 26
       nesum = 3
       csilop = fltarr(nsilop)
       cmpr2 = fltarr(magpri)
       readf,2,form=form1040,csilop,cmpr2
       ccbrsp = fltarr(nfcoil)
       readf,2,form=form1040,ccbrsp
       ecurrt = fltarr(nesum)
       readf,2,form=form1040,ecurrt
       readf,2,form=form1040,pbinj,rvsin,zvsin,rvsout
       readf,2,form=form1040,zvsout,vsurfa,wpdot,wbdot
       readf,2,form=form1040,slantu,slantl,zuperts,chipre
       readf,2,form=form1040,cjor95,pp95,ssep,yyy2
       readf,2,form=form1040,xmmc,cprof,oring,cjor0
       form1042 = '(1x,a42)'
       header = ''
       readf,2,form=form1042,header
       print,header 
    '''
    # file='/home/shiraiwa/a1120912012.01000'
    f = open(file, 'r')

    uday, mfvers = read1055(f)
    ishot, ktime = read_ishotktime(f)
    time = float(f.readline())
    timejj, jflag, lflag, limloc, mco2v, mco2r, qmflag = read1060(f)

    tsaisq, rcencm, bcentr, pasmat = read1040f(f)
    cpasma, rout, zout, aout = read1040f(f)
    eout, doutu, doutl, vout = read1040f(f)
    rcurrt, zcurrt, qsta, betat = read1040f(f)
    betap, ali, oleft, oright = read1040f(f)
    otop, obott, qpsib, vertn = read1040f(f)

    rco2v = read1040_array(f, mco2v)
    dco2v = read1040_array(f, mco2v)
    rco2r = read1040_array(f, mco2r)
    dco2r = read1040_array(f, mco2r)

    shearb, bpolav, s1, s2 = read1040f(f)
    s3, qout, olefs, orighs = read1040f(f)
    otops, sibdry, areao, wplasm = read1040f(f)
    terror, elongm, qqmagx, cdflux = read1040f(f)
    alpha, rttt, psiref, xndnt = read1040f(f)

    rzseps = np.array(read1040(f)).reshape((2, 2))
    rseps = np.transpose(rzseps[0, :])
    zseps = np.transpose(rzseps[1, :])

    sepexp, obots, btaxp, btaxv = read1040f(f)
    aaq1, aaq2, aaq3, seplim = read1040f(f)
    rmagx, zmagx, simagx, taumhd = read1040f(f)
    betapd, betatd, wplasmd, fluxx = read1040f(f)
    vloopt, taudia, qmerci, tavem = read1040f(f)

    val = {}

    val["uday"] = uday
    val["mfvers"] = mfvers
    val["ishot"] = ishot
    val["ktime"] = ktime
    val["time"] = time
    val["timejj"] = timejj
    val["jflag"] = jflag
    val["lflag"] = lflag
    val["limloc"] = limloc
    val["mco2v"] = mco2v
    val["mco2r"] = mco2r
    val["qmflag"] = qmflag
    val["tsaisq"] = tsaisq
    val["rcencm"] = rcencm
    val["bcentr"] = bcentr
    val["pasmat"] = pasmat
    val["cpasma"] = cpasma
    val["rout"] = rout
    val["zout"] = zout
    val["aout"] = aout
    val[" eout"] = eout
    val["doutu"] = doutu
    val["doutl"] = doutl
    val["vout"] = vout
    val["rcurrt"] = rcurrt
    val["zcurrt"] = zcurrt
    val["qsta"] = qsta
    val["betat"] = betat
    val["betap"] = betap
    val["ali"] = ali
    val["oleft"] = oleft
    val["oright"] = oright
    val["otop"] = otop
    val["obott"] = obott
    val["qpsib"] = qpsib
    val["vertn"] = vertn
    val["rco2v"] = rco2v
    val["dco2v"] = dco2v
    val["rco2r"] = rco2r
    val["dco2r"] = dco2r
    val["shearb"] = shearb
    val["bpolav"] = bpolav
    val["s1"] = s1
    val["s2"] = s2
    val["s3"] = s3
    val["qout"] = qout
    val["olefs"] = olefs
    val["orighs"] = orighs
    val["otops"] = otops
    val["sibdry"] = sibdry
    val["areao"] = areao
    val["wplasm"] = wplasm
    val["terror"] = terror
    val["elongm"] = elongm
    val["qqmagx"] = qqmagx
    val["cdflux"] = cdflux
    val["alpha"] = alpha
    val["rttt"] = rttt
    val["psiref"] = psiref
    val["xndnt"] = xndnt
    val["zseps"] = zseps
    val["rseps"] = rseps
    val["sepexp"] = sepexp
    val["obots"] = obots
    val["btaxp"] = btaxp
    val["btaxv"] = btaxv
    val["aaq1"] = aaq1
    val["aaq2"] = aaq2
    val["aaq3"] = aaq3
    val["seplim"] = seplim
    val["rmagx"] = rmagx
    val["zmagx"] = zmagx
    val["simagx"] = simagx
    val["taumhd"] = taumhd
    val["betapd"] = betapd
    val["betatd"] = betatd
    val["wplasmd"] = wplasmd
    val["fluxx"] = fluxx
    val["vloopt"] = vloopt
    val["taudia"] = taudia
    val["qmerci"] = qmerci
    val["tavem"] = tavem

    return val
