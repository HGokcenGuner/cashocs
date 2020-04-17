"""
Created on 01.04.20, 14:22

@author: sebastian
"""

import fenics
import numpy as np
from ...optimization_algorithm import OptimizationAlgorithm
from .unconstrained_line_search import UnconstrainedLineSearch
from ....helpers import summ


class InnerCG(OptimizationAlgorithm):

	def __init__(self, optimization_problem):
		OptimizationAlgorithm.__init__(self, optimization_problem)

		self.line_search = UnconstrainedLineSearch(self)

		self.maximum_iterations = self.config.getint('OptimizationRoutine', 'maximum_iterations_inner_pdas')
		self.tolerance = self.config.getfloat('OptimizationRoutine', 'pdas_inner_tolerance')
		self.reduced_gradient = [fenics.Function(self.optimization_problem.control_spaces[j]) for j in range(len(self.controls))]
		self.first_iteration = True
		self.first_gradient_norm = 1.0

		self.gradients_prev = [fenics.Function(V) for V in self.optimization_problem.control_spaces]
		self.differences = [fenics.Function(V) for V in self.optimization_problem.control_spaces]
		self.temp_HZ = [fenics.Function(V) for V in self.optimization_problem.control_spaces]

		self.stepsize = self.config.getfloat('OptimizationRoutine', 'step_initial')
		self.epsilon_armijo = self.config.getfloat('OptimizationRoutine', 'epsilon_armijo')
		self.beta_armijo = self.config.getfloat('OptimizationRoutine', 'beta_armijo')
		self.armijo_stepsize_initial = self.stepsize
		self.armijo_broken = False

		self.cg_method = self.config.get('OptimizationRoutine', 'cg_method')
		self.cg_use_restart = self.config.getboolean('OptimizationRoutine', 'cg_use_restart')
		self.cg_restart_its = self.config.getint('OptimizationRoutine', 'cg_restart_its')



	def run(self, idx_active):
		self.iteration = 0
		self.memory = 0
		self.relative_norm = 1.0
		self.state_problem.has_solution = False
		for i in range(len(self.gradients)):
			self.gradients[i].vector()[:] = 1.0
			self.reduced_gradient[i].vector()[:] = 1.0

		while True:

			for i in range(self.form_handler.control_dim):
				self.gradients_prev[i].vector()[:] = self.reduced_gradient[i].vector()[:]

			self.adjoint_problem.has_solution = False
			self.gradient_problem.has_solution = False
			self.gradient_problem.solve()

			for j in range(len(self.controls)):
				self.reduced_gradient[j].vector()[:] = self.gradients[j].vector()[:]
				self.reduced_gradient[j].vector()[idx_active[j]] = 0.0

			self.gradient_norm_squared = self.form_handler.scalar_product(self.reduced_gradient, self.reduced_gradient)

			if self.cg_method=='FR':
				self.beta_numerator = self.form_handler.scalar_product(self.reduced_gradient, self.reduced_gradient)
				self.beta_denominator = self.form_handler.scalar_product(self.gradients_prev, self.gradients_prev)
				self.beta = self.beta_numerator/self.beta_denominator

			elif self.cg_method=='PR':
				for i in range(len(self.gradients)):
					self.differences[i].vector()[:] = self.reduced_gradient[i].vector()[:] - self.gradients_prev[i].vector()[:]

				self.beta_numerator = self.form_handler.scalar_product(self.reduced_gradient, self.differences)
				self.beta_denominator = self.form_handler.scalar_product(self.gradients_prev, self.gradients_prev)
				self.beta = self.beta_numerator/self.beta_denominator


			elif self.cg_method=='HS':
				for i in range(len(self.gradients)):
					self.differences[i].vector()[:] = self.reduced_gradient[i].vector()[:] - self.gradients_prev[i].vector()[:]

				self.beta_numerator = self.form_handler.scalar_product(self.reduced_gradient, self.differences)
				self.beta_denominator = self.form_handler.scalar_product(self.differences, self.search_directions)
				self.beta = self.beta_numerator/self.beta_denominator

			elif self.cg_method=='DY':
				for i in range(len(self.gradients)):
					self.differences[i].vector()[:] = self.reduced_gradient[i].vector()[:] - self.gradients_prev[i].vector()[:]

				self.beta_numerator = self.form_handler.scalar_product(self.reduced_gradient, self.reduced_gradient)
				self.beta_denominator = self.form_handler.scalar_product(self.search_directions, self.differences)
				self.beta = self.beta_numerator/self.beta_denominator

			elif self.cg_method=='CD':
				self.beta_numerator = self.form_handler.scalar_product(self.reduced_gradient, self.reduced_gradient)
				self.beta_denominator = self.form_handler.scalar_product(self.search_directions, self.reduced_gradient)
				self.beta = self.beta_numerator/self.beta_denominator

			elif self.cg_method=='HZ':
				for i in range(len(self.gradients)):
					self.differences[i].vector()[:] = self.reduced_gradient[i].vector()[:] - self.gradients_prev[i].vector()[:]

				dy = self.form_handler.scalar_product(self.search_directions, self.differences)
				y2 = self.form_handler.scalar_product(self.differences, self.differences)

				for i in range(len(self.gradients)):
					self.differences[i].vector()[:] = self.differences[i].vector()[:] - 2*y2/dy*self.search_directions[i].vector()[:]

				self.beta = self.form_handler.scalar_product(self.differences, self.reduced_gradient)/dy

			else:
				raise SystemExit('Not a valid method for nonlinear CG. Choose either FR (Fletcher Reeves), PR (Polak Ribiere), HS (Hestenes Stiefel), DY (Dai Yuan), CD (Conjugate Descent) or HZ (Hager Zhang).')

			if self.iteration==0:
				self.gradient_norm_initial = np.sqrt(self.gradient_norm_squared)
				if self.first_iteration:
					self.first_gradient_norm = self.gradient_norm_initial
					self.first_iteration = False
				self.beta = 0.0

			self.relative_norm = np.sqrt(self.gradient_norm_squared)/self.gradient_norm_initial
			if self.relative_norm <= self.tolerance or self.relative_norm*self.gradient_norm_initial/self.first_gradient_norm <= self.tolerance/2:
				self.converged = True
				break

			if not self.cg_use_restart:
				for i in range(self.form_handler.control_dim):
					self.search_directions[i].vector()[:] = -self.reduced_gradient[i].vector()[:] + self.beta*self.search_directions[i].vector()[:]
			elif self.memory < self.cg_restart_its:
				for i in range(self.form_handler.control_dim):
					self.search_directions[i].vector()[:] = -self.reduced_gradient[i].vector()[:] + self.beta*self.search_directions[i].vector()[:]
				self.memory += 1
			else:
				for i in range(len(self.gradients)):
					self.search_directions[i].vector()[:] = -self.reduced_gradient[i].vector()[:]
				self.memory = 0

			self.directional_derivative = self.form_handler.scalar_product(self.reduced_gradient, self.search_directions)

			if self.directional_derivative >= 0:
				for i in range(len(self.gradients)):
					self.search_directions[i].vector()[:] = -self.reduced_gradient[i].vector()[:]

			self.line_search.search(self.search_directions)
			if self.armijo_broken:
				raise SystemExit('Armijo rule failed')
				# print('Armijo rule failed')
				# break

			self.iteration += 1
			if self.iteration >= self.maximum_iterations:
				break

		# if self.converged:
			# self.print_results()

		# print('')
		# print('Statistics --- Total iterations: ' + format(self.iteration, '4d') + ' --- Final objective value:  ' + format(self.objective_value, '.3e') +
		# 	  ' --- Final gradient norm:  ' + format(self.relative_norm, '.3e') + ' (rel)')
		# print('           --- State equations solved: ' + str(self.state_problem.number_of_solves) +
		# 	  ' --- Adjoint equations solved: ' + str(self.adjoint_problem.number_of_solves))
		# print('')