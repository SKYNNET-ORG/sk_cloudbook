import logging

def clean_matrix_old(config_dict):
	logging.info(">>>Enter in clean matrix")
	matrix = config_dict["matrix"]
	clean=False
	while (clean==False):
		num_cols=len(matrix[0])
		num_rows=len(matrix)
		row_to_clean=-1
		#print ("cleaning matrix... rows=",num_rows)
		#print_matrix(matrix)

		for i in range(num_rows-1,1,-1):
			suma=0
			for j in range(1,num_cols):
				suma+=matrix[i][j]
			#for j in range(1,num_cols):#TODO: If cloudbook main is mandatory, this is not necessary, only check if a function is main and not delete it
				#suma+=matrix[j][i]

			if (suma==0):
				if config_dict["matrix"][i][0] == config_dict["pragmas"]["main"]:
					row_to_clean = -1
				else:
					row_to_clean = i
				#row_to_clean=i
				logging.info(f"Removing row {i}")
				break

		#print ("row to clean: ",row_to_clean)

		if row_to_clean==-1 or row_to_clean==1: # main is row 1
			clean=True

		else:
			#print("borro",matrix[i][0], "sumaa", suma)
			#remove_function_and_DU(con, matrix[i][0]) # must be done before update matrix
			matrix =remove_row(matrix, row_to_clean)
			row_to_clean=-1
	config_dict["matrix"] = matrix
	#print_matrix(config_dict["matrix"])
	#return matrix
	logging.info("<<<Exit from clean matrix")

def clean_matrix(config_dict):
	logging.info(">>>Enter in clean matrix")
	matrix = config_dict["matrix"]
	clean=False
	num_rows=len(matrix)
	num_cols=len(matrix[0])
	rows_to_clean = []
	for i in range(1,num_rows):
		suma = 0
		for j in range(1,num_cols):
			suma+=matrix[i][j]
		if suma == 0:
			if config_dict["matrix"][i][0] == config_dict["pragmas"]["main"]:
				pass
			else:
				rows_to_clean.append(i)
	logging.info("Rows to remove %s",rows_to_clean)
	matrix = remove_rows(matrix,rows_to_clean)
	config_dict["matrix"] = matrix
	logging.info("<<<Exit from clean matrix")

def remove_row(matrix, row_to_clean):
	logging.info("	>>>Enter in remove row")
	#print "cleaning row ", row_to_clean
	num_cols=len(matrix[0])
	num_rows=len(matrix)
	matrix_new2= [[None] * (num_cols-1) for i in range(num_rows-1)]
	row2=0
	col2=0
	for i in range(0,num_rows):
		if (i==row_to_clean):
			continue
		for j in range(0,num_cols):
			if (j==row_to_clean):
				continue
			matrix_new2[row2][col2]=matrix[i][j]
			col2+=1
		row2+=1
		col2=0

	matrix=matrix_new2
	##print_matrix(matrix)
	logging.info("	<<<Exit from remove row")
	return matrix

def print_matrix(matrix):
	num_cols=len(matrix[0])
	num_rows=len(matrix)
	for i in range(0,num_rows):
		print (matrix[i])

def remove_rows(matrix, rows_to_clean):
	logging.info("	>>>Enter in remove row")
	#print "cleaning row ", row_to_clean
	num_cols=len(matrix[0])
	num_rows=len(matrix)
	matrix_new2= [[None] * (num_cols-len(rows_to_clean)) for i in range(num_rows-len(rows_to_clean))]
	row2=0
	col2=0
	for i in range(0,num_rows):
		if (i in rows_to_clean):
			continue
		for j in range(0,num_cols):
			if (j in rows_to_clean):
				continue
			matrix_new2[row2][col2]=matrix[i][j]
			col2+=1
		row2+=1
		col2=0

	matrix=matrix_new2
	##print_matrix(matrix)
	logging.info("	<<<Exit from remove row")
	return matrix
