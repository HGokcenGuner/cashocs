"""
Created on 15/06/2020, 16.11

@author: blauths
"""

from fenics import *
from adoptpy import ShapeOptimizationProblem, import_mesh
import numpy as np
import configparser



set_log_level(LogLevel.CRITICAL)

config = configparser.ConfigParser()
config.read('./config.ini')

mesh, subdomains, boundaries, dx, ds, dS = import_mesh('./mesh/mesh.xdmf')

x = SpatialCoordinate(mesh)
volume_initial = 4**2*9 - assemble(Constant(1)*dx)
barycenter_x_initial = (1/2*(6**2 - 3**2)*4*4 - assemble(x[0]*dx)) / volume_initial
barycenter_y_initial = (1/2*(2**2 - 2**2)*9*4 - assemble(x[1]*dx)) / volume_initial
barycenter_z_initial = (1/2*(2**2 - 2**2)*9*4 - assemble(x[2]*dx)) / volume_initial

v_elem = VectorElement('CG', mesh.ufl_cell(), 2)
p_elem = FiniteElement('CG', mesh.ufl_cell(), 1)
space = FunctionSpace(mesh, MixedElement([v_elem, p_elem]))

v_in = Expression(('1.0/16.0*(x[1] - 2.0)*(x[1] + 2.0)*(x[2] - 2.0)*(x[2] + 2.0)', '0.0', '0.0'), degree=4)
bc_in = DirichletBC(space.sub(0), v_in, boundaries, 1)
bc_wall = DirichletBC(space.sub(0), Constant((0, 0, 0)), boundaries, 2)
bc_gamma = DirichletBC(space.sub(0), Constant((0, 0, 0)), boundaries, 4)
bcs = [bc_in, bc_wall, bc_gamma]


up = Function(space)
u, p = split(up)
vq = Function(space)
v, q = split(vq)

[bc.apply(up.vector()) for bc in bcs]


e = inner(grad(u), grad(v))*dx - p*div(v)*dx - q*div(u)*dx

J = inner(grad(u), grad(u))*dx

optimization_problem = ShapeOptimizationProblem(e, bcs, J, up, vq, boundaries, config)
optimization_problem.solve()
# optimization_problem.state_problem.solve()

u, p = up.split(True)

volume = 4**2*9 - assemble(Constant(1)*dx)
barycenter_x = (1/2*(6**2 - 3**2)*4*4 - assemble(x[0]*dx)) / volume
barycenter_y = (1/2*(2**2 - 2**2)*9*4 - assemble(x[1]*dx)) / volume
barycenter_z = (1/2*(2**2 - 2**2)*9*4 - assemble(x[2]*dx)) / volume
