@/usr/local/cmod/codes/efit/idl/efit_rz2rho.pro

function nete_ispline, shot, time
  mdsopen, "electrons", shot
  
  time = mdsvalue('_time = '+strtrim(time, 2))
  cne= mdsvalue('\ELECTRONS::TOP.YAG_NEW.RESULTS.PROFILES:NE_RZ[_time,*]')
  cne_err=mdsvalue('\ELECTRONS::TOP.YAG_NEW.RESULTS.PROFILES:NE_ERR[_time,*]')  
  cte = mdsvalue('\ELECTRONS::TOP.YAG_NEW.RESULTS.PROFILES:TE_RZ[_time,*]')
  cte_err=mdsvalue('\ELECTRONS::TOP.YAG_NEW.RESULTS.PROFILES:TE_ERR[_time,*]')  
  x = mdsvalue('\ELECTRONS::TOP.YAG_NEW.RESULTS.PROFILES:RHO_T[_time,*]')
  r = mdsvalue('\ELECTRONS::TOP.YAG.RESULTS.PARAM:R')
  z = mdsvalue('\ELECTRONS::TOP.YAG_NEW.RESULTS.PROFILES:Z_SORTED')
  z = mdsvalue('dim_of(\ELECTRONS::TOP.YAG_NEW.RESULTS.PROFILES:TE_RZ[_time,*],1)')

  r=dblarr(n_elements(z))+r
;  c_rho=efit_rz2rho(r,z,time, shot=shot, time=time, phinorm=1, sqrt=1)
  c_rho=efit_rz2rho(r,z,time, shot=shot, phinorm=1, sqrt=1)


  ene= mdsvalue('\ELECTRONS::TOP.YAG_EDGETS.RESULTS:NE[_time,*]')
  ene_err= mdsvalue('\ELECTRONS::TOP.YAG_EDGETS.RESULTS:NE:ERROR[_time,*]')
  ete= mdsvalue('\ELECTRONS::TOP.YAG_EDGETS.RESULTS:TE[_time,*]')
  ete_err= mdsvalue(' \ELECTRONS::TOP.YAG_EDGETS.RESULTS:TE:ERROR[_time,*]')
  ex= mdsvalue('\ELECTRONS::TOP.YAG_EDGETS.RESULTS:RHO[_time,*]')
  z = mdsvalue('\ELECTRONS::TOP.YAG_EDGETS.DATA:FIBER_Z')
  r=dblarr(n_elements(z))+r[0]
  ;e_rho=efit_rz2rho(r,z,time, shot=shot, time=time, phinorm=1, sqrt=1)
  e_rho=efit_rz2rho(r,z,time, shot=shot, phinorm=1, sqrt=1)

  idx=sort(e_rho)
  e_rho=e_rho[idx]
  ene=ene[idx]
  ene_err=ene_err[idx]
  ete=ete[idx]
  ete_err=ete_err[idx]

  idx=sort(c_rho)
  c_rho=c_rho[idx]
  cne=cne[idx]
  cne_err=cne[idx]
  cte=cte[idx]
  cte_err=cte[idx]

  return,{cne:cne,  cne_err:cne_err,  $
          cte:cte,  cte_err:cte_err,  $
          c_rho:c_rho, $
          ene:ene,  ene_err:ene_err,  $
          ete:ete,  ete_err:ete_err,  $
          e_rho:e_rho}

end
