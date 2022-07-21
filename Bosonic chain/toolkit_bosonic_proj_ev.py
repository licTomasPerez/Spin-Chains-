# In [1]:

import qutip
import numpy as np
import scipy.optimize as opt 
import pickle
import sys
import scipy.linalg as linalg

# In [2]:

def ev_checks(rho):
    a = bool; ev_list = linalg.eig(rho)[0]
    for i in range(len(ev_list)):
        if (ev_list[i] > 0):
            a = True
        else:
            a = False
            print("Eigenvalues not positive")
    return a

def is_density_op(rho):
    return (qutip.isherm(rho) and (rho.tr() == 1 or (1 - rho.tr() < 10**-10)) and ev_checks(rho)) 

# In [3]: 
# In [8]: 

natural = tuple('123456789')

def n_body_basis(gr, N):
    basis = []
    globalid_list, sx_list, sy_list, sz_list = one_body_spin_ops(N)
    
    if (isinstance(gr,int) and str(gr) in natural):
        try:
            if (gr == 1):
                basis = globalid_list + sx_list + sy_list + sz_list
            elif (gr > 1):
                basis = [op1*op2 for op1 in n_body_basis(gr-1, N) for op2 in n_body_basis(1, N)]
        except Exception as ex:
            basis = None
            print(ex)
    return basis

# In [9]:

def n_body_max_ent_state(gr, N, coeffs = list, build_all = True, visualization = False):
    K = 0; rho_loc = 0;
    
    loc_globalid = qutip.tensor([qutip.qeye(2) for k in range(N)]) 
    loc_id_list, sx_list, sy_list, sz_list = one_body_spin_ops(N)
    pauli_vec = [sx_list, sy_list, sz_list];
    
    if (gr == 1):
        try:
        
        except Exception as exme1:
            print(exme1, "Max-Ent 1 Failure")
            raise exme1
    elif (gr == 2): 
        try:
        except Exception as exme2:
            print(exme2, "Max-Ent 2 Failure")
            raise exme2
    else:
        print('gr must be either 1 or 2')
    
    rho_loc = K.expm()
    rho_loc = rho_loc/rho_loc.tr()
    
    if is_density_op(rho_loc):
        pass
    else:  
        rho_loc = None 
        raise Exception("The result is not a density operator")
        
    if visualization: 
        qutip.hinton(rho_loc)
        
    return rho_loc 

#In [10]:

def prod_basis(b1, b2):
    return [qutip.tensor(b,s) for b in b1 for s in b2]

def scalar_prod(op1, op2, rho0 = None, HS_prod_modified = True):
    if op1.dims[0][0]==op2.dims[0][0]:
        pass
    else:
        raise Exception("Incompatible Qobj dimensions")
    if rho0 is None:
        rho0 = qutip.qeye(op1.dims[0])/op1.dims[0][0]
    if (HS_prod_modified):  
        result = .5*(rho0*(op1*op2.dag()+op2.dag()*op1)).tr()
    else: 
        result = .5*(rho0*(op1.dag()*op2)).tr()
    return result.real

def base_orth(ops, rho0):
    if isinstance(ops[0], list):
        ops = [op for op1l in ops for op in op1l]
    dim = ops[0].dims[0][0]
    basis = []
    for i, op in enumerate(ops): 
        alpha = [scalar_prod(op2, op, rho0) for op2 in basis]
        op_mod = op - sum([c*op2 for c, op2, in zip(alpha, basis)])
        op_norm = np.sqrt(scalar_prod(op_mod,op_mod,rho0))
        if op_norm<1.e-12:
            continue
        op_mod = op_mod/(op_norm)
        basis.append(op_mod)
    return basis

def logM(rho):
    if ev_checks(rho):
        pass
    else:
        raise Exception("Singular input matrix")
    eigvals, eigvecs = rho.eigenstates()
    return sum([np.log(vl)*vc*vc.dag() for vl, vc in zip(eigvals, eigvecs)])

def sqrtM(rho):
    if qutip.isherm(rho) and ev_checks(rho):
        pass
    else:
        raise Exception("Non-hermitian or singular input matrix")
    eigvals, eigvecs = rho.eigenstates()
    return sum([(vl**.5)*vc*vc.dag() for vl, vc in zip(eigvals, eigvecs)])

def proj_op(K, basis, rho0):
    return sum([scalar_prod(b, K,rho0) * b for b in basis])

def rel_entropy(rho, sigma):
    if (ev_checks(rho) and ev_checks(sigma)):
        pass
    else:
        raise Exception("Either rho or sigma non positive")
    
    val = (rho*(logM(rho)-logM(sigma))).tr()
                    
    if (abs(val.imag)>1.e-6):
        val = None
        raise Exception("Either rho or sigma not positive")
    return val.real
                
# In [11]:

def bures(rho, sigma):
    if is_density_op(rho) and is_density_op(sigma):
        val = abs((sqrtM(rho)*sqrtM(sigma)).tr())
        val = max(min(val,1.),-1.)
    return np.arccos(val)/np.pi
        
def maxent_rho(rho, basis):   
    def test(x, rho, basis):
        k = sum([-u*b for u,b in zip(x, basis)])        
        sigma = (.5*(k+k.dag())).expm()
        sigma = sigma/sigma.tr()
        return rel_entropy(rho, sigma)    
    res = opt.minimize(test,zeros(len(basis)),args=(rho,basis))
    k = sum([-u*b for u,b in zip(res.x, basis)])        
    sigma = (.5*(k+k.dag())).expm()
    sigma = sigma/sigma.tr()
    return sigma
 
def error_maxent_state(rho, basis, distance=bures):
    try:
        sigma = maxent_rho(rho, basis)
        return distance(rho,sigma)
    except:
        print("fail error max-ent state")
        return None
       
def error_proj_state(rho, rho0, basis, distance=bures):
    try:
        basis = base_orth(basis, rho0)
    except:
        print("orth error")
        raise
    try:
        sigma = proj_op(logM(rho), basis, rho0).expm()
        sigma = (sigma+sigma.dag())/(2.*sigma.tr())
    except:
        print("gram error")
    try:
        return distance(rho, sigma)
    except:
        print("fail error proj state")
        return None
    
# In [12]:

def spin_dephasing(N, gamma):
    loc_c_op_list = []; sz_list = one_body_spin_ops(N)[3];
    collapse_weights = abs(gamma) * np.ones(N)
    loc_c_op_list = [np.sqrt(collapse_weights[n]) * sz_list[n] for n in range(N)]
    return loc_c_op_list

# In [13]:

def initial_state(N = 1, gaussian = True, gr = 1, x = .5, coeffs = list, psi0 = qutip.Qobj,
                  visualization=False):
    loc_globalid = qutip.tensor([qutip.qeye(2) for k in range(N)]) 
    if gaussian: 
        rho0 = n_body_max_ent_state(gr, N, coeffs)
    else:
        if (qutip.isket(psi0)):
            rho0 = psi0 * psi0.dag()
            rho0 = x * rho0 + (1-x)*loc_globalid * x/N
            rho0 = rho0/rho0.tr()
        else:
            print("Psi0 must be a ket")
    
    if is_density_op(rho0):
        pass
    else: 
        rho0 = None
        print("Output is not a density operador")
    
    if visualization:
            qutip.hinton(rho0)
    
    return rho0     