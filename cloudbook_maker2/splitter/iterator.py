#iterates over the functions matrix
import logging
from . import collapser
from .import collapser_selector
import json

def iterate(config_dict):
	logging.info(">>>ENTER in iterate()...")
	''' this function receives the matrix as input and the number of desired DUs.
		The desired number of DUs will be (normally) the number of available machines.
		Therefore the final number of DUs must be equal or bigger than number of desired DUs.
		Without any iteration, the number of DU is the number of functions.
		The matrix will be colapsed iteratively, reducing the number of DUs, by colapsing the 
		pair of functions which invoke each other more times.
		when the number of DU is equal to number of desired DUs, then the process stops'''

	#first step is to clean matrix. remove functions if they are not invoked
	#matrix=clean_matrix(matrix)
		
	#iteration 0. Num DUs is the number of functions
	matrix=config_dict["matrix"]
	desired_num_du=config_dict["num_dus"]

	num_du= len(matrix[0])-1

	len_collapsable=2 #initially nothing is collapsed. At this point 2 funcs are collapsable
	while(num_du>desired_num_du):		
		
		collapser_function=collapser_selector.get_collapser(0);

		(f2_col,f1_col)= collapser_function(matrix)
		f2_row=f2_col
		f1_row=f1_col
		#len_collapsable =len(matrix[0][f1_col])
			
		if (f2_row==0 and f1_col==0):
			#print "not possible to collapse more"
			return matrix

		#print "collapsing functions..."
		matrix=collapser.collapse(matrix,f1_row,f2_row)#, con)

		num_du= len(matrix)-1
		logging.debug("	Num dus actuales "+ str(num_du)+ " frente a " + str(desired_num_du))

		#print "matrix:"
		#print_matrix(matrix_new2)
		
	logging.debug(">>>EXIT from iterate()...")
	config_dict["matrix"] = matrix
	logging.debug("=======================")
	return matrix

	#return iterate_fake(con,matrix,desired_num_du)


def print_matrix(matrix):
	num_cols=len(matrix[0])
	num_rows=len(matrix)
	for i in range(0,num_rows):
		print (matrix[i])


