"""
Created on 13/08/2020, 12.55

@author: blauths
"""

from fenics import *
import adoptpy



set_log_level(LogLevel.CRITICAL)
config = adoptpy.create_config('config.ini')

mesh, subdomains, boundaries, dx, ds, dS = adoptpy.regular_mesh(50)
V = FunctionSpace(mesh, 'CG', 1)

y = Function(V)
p = Function(V)
u = Function(V)

e = inner(grad(y), grad(p))*dx - u*p*dx

bcs = adoptpy.create_bcs_list(V, Constant(0), boundaries, [1, 2, 3, 4])

y_d = Expression('sin(2*pi*x[0])*sin(2*pi*x[1])', degree=1)
alpha = 1e-6
J = Constant(0.5)*(y - y_d)*(y - y_d)*dx + Constant(0.5*alpha)*u*u*dx

u_a = interpolate(Expression('50*(x[0]-1)', degree=1), V)
u_b = interpolate(Expression('50*x[0]', degree=1), V)

cc = [u_a, u_b]

ocp = adoptpy.OptimalControlProblem(e, bcs, J, y, u, p, config, control_constraints=cc)
ocp.solve()

import numpy as np
assert np.alltrue(u_a.vector()[:] <= u.vector()[:]) and np.alltrue(u.vector()[:] <= u_b.vector()[:])