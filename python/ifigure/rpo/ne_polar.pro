;Input:- shot:shot number
;Potential outputs:
;       - r_p: major radius for points on polarimeter path,same for
;         all chords   [m]
;       - z_p(i,j): vertical position for points on polar path, i for
;         different chords, j for differnt points  [m]
;       - den_p(i,j,k): density for points on polar path, i for
;         chords,j for different points,k for efit time  [m^-3]
;       - t: efit time  [s]
;       - FaradayR(i,k):polarimeter phase on chord i and time k [deg]

; -----------------------------------------------------------------\
pro type_variable, var
   print, size(var, /n_dim)
   print, size(var, /dim)
   print, var
end

pro ne_polar,shot ;get Thomson density data on polarimter paths

;geometry information for different chords
mdsopen,'electrons',shot
retro_p=mdsvalue('\ELECTRONS::TOP.POLARIMETER.RESULTS:CHORDS_POS')
z_retro=retro_p(1,*)
rw=retro_p(0,0)
chord_act=mdsvalue('\ELECTRONS::TOP.POLARIMETER.RESULTS:CHORDS_ACT')
nchord=total(chord_act)
chord_ind=where(chord_act eq 1)
zo=9.875*0.0254   
ro=53.115*0.0254  
mdsclose

;get efit good time
MDSOPEN,'ANALYSIS',shot,status=status,/quiet
icur_EFIT=mdsvalue('\ANALYSIS::efit_aeqdsk:cpasma',status=status,/quiet) 
tefit=MDSVALUE('dim_of(\ANALYSIS::EFIT_AEQDSK:vout)')
igood=efit_check(tgood,ngood)
t=tefit(igood)    ;efit time t

;get Thomson density profiles from quickfit
restore,strcompress('/home/xupeng/idl/quickfit/quickfit_'+string(shot)+'.save',/remove_all) 
n=afp(*,*,0)*1.e20 ;density profile
num_r=n_elements(ax)
num_t=n_elements(t)
nTime=findgen(num_t,num_r)
rTime=findgen(num_t,num_r)
;interpol from TS time to EFIT time t
for p=0,num_r-1 do begin
   nTime[*,p]=interpol(n[*,p],T_TS,t)
   rTime[*,p]=interpol(r_out,T_TS,t)+ax(p);minor radius(ax)+r_out= major radius
endfor

;mapping density from midplane to psi-space, finally to r_z
 MdsSetDefault,'\efit_geqdsk'
 rgrid = MdsValue('rgrid')
 zgrid = MdsValue('zgrid')
 mw = MdsValue('mw')
 mh = MdsValue('mh')

;r=findgen(nchord,mw)
r_p=findgen(mw)
z_p=findgen(nchord,mw)
den_p=findgen(nchord,mw,num_t)

for p=0,num_t-1 do begin
 time=t(p)
 psirz = MdsValue('psirz[*,*,$]',time)
 ssimag = MdsValue('ssimag[$]',time)
 ssibry = MdsValue('ssibry[$]',time)
 psinorm=(psirz-ssimag)/(ssibry-ssimag)
;------------------------------------------
;get rid of data outside the min,max TS radius 
irs=where(rgrid ge min(rTime[p,*]) and rgrid le max(rTime[p,*]))
psirz2=psirz[irs,*]
rgrid2=rgrid[irs]
;---------------------------------------------
cubic=-0.5 
psirz2=congrid(psirz2,mw,mh,cubic=cubic,/minus_one)
psinorm2=(psirz2-ssimag)/(ssibry-ssimag)
rgrid2=interpol(rgrid2,mw)
;zgrid2=interpol(zgrid,mh)

nrgrid=interpol(nTime[p,*],rTime[p,*],rgrid2)
;find z index for midplane
minz=min(abs(zgrid),izn)
;make 1d psi array for midplane
psir=psinorm2[*,izn]
;set up 2d density array
den=fltarr(mw,mh)
;fill density array stepping up in psi[0,1]
ssep=1.0
for i=0,40 do begin
  izr=where(psir ge 0.025*i)
  izzr=where(psinorm ge 0.025*i)
  irm=min(izr)
  if irm eq -1 then break
  ntemp=nrgrid[irm]
  den[izzr]=ntemp
endfor

;density expenential decay outside of separatrix 
iz=where(psinorm lt ssep and psinorm gt ssep-.01,nz)
if(nz gt 0) then densep=avg(den(iz))
iz=where(psinorm ge ssep)
den(iz)=densep*exp((1-psinorm(iz))*25.)

iz=where(abs(zgrid) gt .5,nz)  ;den=0 where zgrid>0.5m
if(nz ge 1) then den(*,iz)=0.0

;-----------------
;map density to different chords
for i=0,nchord-1 do begin
    zw=z_retro(chord_ind(i))
    theta=atan(zo-zw,ro-rw)
    for j=0,mw-1 do begin
    r_p(j)=rgrid(j)
    z_p(i,j)=zw+(r_p(j)-rw)*tan(theta)
    den_p(i,j,p)=interpol(reform(den(j,*)),zgrid,z_p(i,j)) ;at time t(p)
    endfor
endfor
endfor
mdsclose
;--------------------------------------------------------------------------
;read polarimter phase data and interpol to EFIT time t
mdsopen,'electrons',shot
FR1=mdsvalue('\ELECTRONS::TOP.POLARIMETER.RESULTS:FROT_01_SL')
FR2=mdsvalue('\ELECTRONS::TOP.POLARIMETER.RESULTS:FROT_02_SL')
FR3=mdsvalue('\ELECTRONS::TOP.POLARIMETER.RESULTS:FROT_03_SL')
T_FR=mdsvalue('dim_of(\ELECTRONS::TOP.POLARIMETER.RESULTS:FROT_01_SL)')
FR=[[FR1],[FR2],[FR3]]
FaradayR=fltarr(nchord,num_t)
for i=0,nchord-1 do begin
   FaradayR[i,*]=interpol(FR[*,i],T_FR,t)
end
mdsclose
; -----------------------------------------------------------------
type_variable,r_p
type_variable,z_p
type_variable,den_p
type_variable,t
type_variable,FaradayR

end
