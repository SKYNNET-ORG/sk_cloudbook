import logging


# low latency ONLY collapser

def choose_functions_to_collapse (matrix):
	logging.debug("		>>>Getting functions to collapse")
	#compute the maximum value of matrix to determine which functions to collapse
	#----------------------------------------------------------------------------

	num_cols=len(matrix[0])
	num_rows=len(matrix)
	#print "\n num_cols = ",num_cols, " num_rows = ",num_rows, "\n"
	max_invocations=0
	f1_row=0
	f1_col=0
	f2_row=0
	f2_col=0
	#len_collapsable=2 #initially nothing is collapsed. At this point 2 funcs are collapsable

	for i in range(1,num_rows):
		for j in range(1,num_cols):
			# self-invocation is not relevant
			if (i!=j) and (matrix[i][j] >= max_invocations):
				#if (matrix[i][j] == max_invocations):
					#if (len(matrix[0][j])>len_collapsable):
					#	continue

				# best candidate selection
				max_invocations=matrix[i][j]
				f2_col=i # f2 invocation column is the row
				f1_col=j # f1 invocation column is the column
				f1_row=f1_col
				f2_row=f2_col
				#len_collapsable =len(matrix[0][j])
	logging.debug("		Functions to collapse: %s,%s",f2_col,f1_col)
	return (f2_col,f1_col)
