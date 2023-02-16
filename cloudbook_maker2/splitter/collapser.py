
# This module collapse the matrix using the selected 2 functions 

import json
import logging

def collapse(matrix, f1_row,f2_row):#,con):
	logging.debug("	>>>ENTER in collapse...")
	f1_col=f1_row
	f2_col=f2_row
	#collapse functions matrix[0][f1_col] and matrix[0][f1_row]
	#----------------------------------------------------------------------------
	num_cols=len(matrix[0])
	num_rows=len(matrix)
	matrix_new= [[None] * (num_cols) for i in range(num_rows)]


	#copy matrix
	for i in range(0,num_rows):
		for j in range(0,num_cols):
			if (matrix[i][j]==None) :
				matrix[i][j]=0
			matrix_new[i][j]=matrix[i][j]
			#print("El elemento ", matrix_new[i][j], " es de tipo: ", type(matrix_new[i][j]))
	

	#update DU identifier
	#---------------------

	##update_DU(con, matrix_new[0][f2_col],matrix_new[0][f1_col])

	# collapse titles
	# -----------------
	# new function is a list of two functions ( f1 and f2 may be lists of functions)
	# we must create a new list composed of all items from list f1 and all intems from list f2
	# if f1 is a list, we extract items, else we simply add f1. The same for f2
	composite_list=[]
	if  isinstance(matrix_new[0][f1_col],list):
		for item in matrix_new[0][f1_col]:
			composite_list.append(item)
	else:
		composite_list.append(matrix_new[0][f1_col])

	if  isinstance(matrix_new[0][f2_col],list):
		for item in matrix_new[0][f2_col]:
			composite_list.append(item)
	else:
		composite_list.append(matrix_new[0][f2_col])


	#matrix_new[0][f1_col] = [matrix_new[0][f1_col],matrix_new[0][f2_col]]
	matrix_new[0][f1_col] = composite_list
	
	matrix_new[f1_row][0] = matrix_new[0][f1_col] 


	#collapse column and row values
	#------------------------------
	for i in range(1,num_rows):
		for j in range(1,num_cols):

			#when column = f2 column, just update f1+f2 column and set to zero f2 column
			if (j==f1_col):
				matrix_new[i][j]+=matrix[i][f2_col]
				matrix_new[i][f2_col]=0 # now f2 not invoke nothing
			if (i==f2_row):
				matrix_new[f1_row][j]+=matrix[i][j]	
				matrix[i][j]=0	
			
	
	#delete column f2 and row f2
	#----------------------------
	matrix_new2= [[None] * (num_cols-1) for i in range(num_rows-1)]
	row2=0
	col2=0
	for i in range(0,num_rows):
		if (i==f2_row):
			continue
		for j in range(0,num_cols):
			if (j==f2_col):
				continue
			matrix_new2[row2][col2]=matrix_new[i][j]
			col2+=1
		row2+=1
		col2=0

	#matrix=matrix_new2
	logging.debug("	>>>Matrix Collapsed")
	return matrix_new2



