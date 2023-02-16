import json
import loader
import datetime
import os
import sys
import time
import platform

from pathlib import Path


### MATRIX.JSON FORMAT ###
# Matrix is saved by rows.
# The first element of each row is the name of the invoked function.
# The first element of each column is the name of the invoker function.

# Example of matrix: [["Matrix", "hanoi.move_tower", "hanoi.main"], ["hanoi.move_tower", 2, 1], ["hanoi.main", 0, 0]]
# [
# 	["Matrix",					"hanoi.move_tower",		"hanoi.main"	],
# 	["hanoi.move_tower",		2,						1				],
# 	["hanoi.main",				0,						0				]
# ]

### STATS_AGENT_XX.JSON FORMAT ###
# It is a dictionary which keys are the invoked function names and the value is also a dictionary. The inner dictionary keys are the invoker function names
# and their value is the number of times that the function name of the column invoked the function name of the row in the time between stats creation
# { invoked_fun1: {invoker_fun1: K,  invoker_fun2: L, ...},  invoked_fun2: {invoker_fun1: M,  invoker_fun2: N ...}, ... }
# Numbers are never 0, but may not contain all the keys for every function (either invoker or invoked)

# Example of stats_agent_XX.json: { "f0": {"f1": 1, "f0": 11}, "f5": {"f3": 4} }
# {
# 	"f0": {
# 		"f1": 1,
# 		"f0": 11
# 	},
# 	"f5": {
# 		"f3": 4,
# 	}
# }


##############################################################
def sum_all_items_matrix(matrix):
	suma=0
	len_row=len(matrix[0])
	for row in range(1,len_row):
		for col in range(1,len_row):
			suma+=matrix[row][col]
	return suma

##############################################################
def compare_matrix(old_matrix,matrix):
	
	#first sumation of all values
	suma_old=sum_all_items_matrix(old_matrix)
	suma=sum_all_items_matrix(matrix)

	len_row=len(old_matrix[0])
	print("len_row",len_row)
	
	ratio=1
	num_updates_ratio=0
	for row in range(1,len_row):
		for col in range(1,len_row):
			print("old:",+old_matrix[row][col], "   new:",+matrix[row][col])
			ratio_new =(suma)//(1+matrix[row][col])
			ratio_old =(suma_old)//(1+old_matrix[row][col])
			print("ratios:", ratio_old,ratio_new)
			ratio=ratio_new//ratio_old
			if ratio>1:
				return True
	return False

#############################################################
def matrix_get(invoker_fun, invoked_fun):
	# Search the coincidence of invoker in the first row
	invoker_fun_index = 0
	for i in matrix[0]:
		if i==invoker_fun:
			break
		invoker_fun_index += 1

	# Search the coincidence of invoked in the first column
	invoked_fun_index = 0
	for i in matrix:
		if i[0]==invoked_fun:
			break
		invoked_fun_index += 1

	# Return the value in the cell with that invoker and invoked
	print("         --> Indexes of", invoker_fun, "(invoker_fun)", invoked_fun, "(invoked_fun) are matrix[", invoked_fun_index, "][", invoker_fun_index, "]")
	return matrix[invoked_fun_index][invoker_fun_index]

#############################################################
def matrix_set(invoker_fun, invoked_fun, value):
	# Search the coincidence of invoker in the first row
	invoker_fun_index = 0
	for i in matrix[0]:
		if i==invoker_fun:
			break
		invoker_fun_index += 1

	# Search the coincidence of invoked in the first column
	invoked_fun_index = 0
	for i in matrix:
		if i[0]==invoked_fun:
			break
		invoked_fun_index += 1

	# Set the value of the cell with that invoker and invoked to the value passed as parameter
	matrix[invoked_fun_index][invoker_fun_index] = value

################################################################################################
def timestamp():
	x=datetime.datetime.now()
	return x.strftime("%b %d %Y %H:%M:%S |")

################################################################################################
def timestamp_file():
	now=datetime.datetime.now()
	return now.strftime("%Y%m%d%H%M%S")

################################################################################################
def get_stats(input_dir, delete_stats_files):
	cumulated_stats={}
	print("----")
	for i in matrix:
		print(i)

	print("reading agents stats...")
	agents_with_grant = {}
	agents_files = []
	agents_files = os.listdir(input_dir+"/stats")
	print("agent stat files:", agents_files)

	print("--------------------------------")
	# For each of the statistics files
	for file in agents_files:
		if file.startswith("stats_agent_") and file.endswith(".json"):
			print("loading file: "+file+" ...")
			agent_stats_dict = loader.load_dictionary(input_dir+"/stats/"+file)
			print("   agent_stats_dict --> ", agent_stats_dict)

			# For each of the invoked functions
			for invoked_fun in agent_stats_dict:
				# Looking for: "thread_counter"
				if invoked_fun=="thread_counter":
					continue

				# Looking for: "critical_section_control"
				elif invoked_fun=="critical_section_control":
					continue

				# Looking for: "nonblocking_inv_x_ORIGNAME" with x a number and ORIGNAME the original function name but without the path (fun() instead of nbody.fun())
				elif invoked_fun.startswith("nonblocking_inv_"):
					incomplete_invoked_orig_name = "_".join(invoked_fun.split("_")[3:])	# Take the name from the 3rd underscore onwards 
					for func_name in matrix[0][1:]:										# For each of the possible names (first row of matrix without "MATRIX")
						if func_name.split(".")[-1]==incomplete_invoked_orig_name:			# If there is a match with the last part after a dot
							invoked_orig_name = func_name										# Assign that name
							break																# Stop iterating
					if incomplete_invoked_orig_name==invoked_orig_name:					# If they are equal, there was no partial match (unknown orig name)
						continue															# Skip this data

				# Looking for: "FUNCNAME"
				else:
					invoked_orig_name = function_inverse_map[invoked_fun]
				print("     processing invoked_fun:", invoked_fun, " --> invoked_orig_name:", invoked_orig_name)


				# For each of the invoker functions
				for invoker_fun in agent_stats_dict[invoked_fun]:
					# Looking for: "thread_counter"
					if invoker_fun=="thread_counter":
						continue

					# Looking for: "critical_section_control"
					elif invoker_fun=="critical_section_control":
						continue

					# Looking for: "nonblocking_inv_FUNCNAME"
					elif invoker_fun.startswith("nonblocking_inv_"):
						invoker_orig_name = function_inverse_map["_".join(invoker_fun.split("_")[2:])]

					# Looking for: "FUNCNAME"
					else:
						invoker_orig_name = function_inverse_map[invoker_fun]
					print("       processing invoker_fun:", invoker_fun, " --> invoker_orig_name:", invoker_orig_name)

					# Get the old value from the matrix
					previous_value = matrix_get(invoker_orig_name, invoked_orig_name)
					adding_value = agent_stats_dict[invoked_fun][invoker_fun]
					final_value = previous_value + adding_value
					print("       ", previous_value, "(previous_value) +", adding_value, "(adding_value) = ", final_value, "(final_value)")

					# Assign the new value to the matrix
					matrix_set(invoker_orig_name, invoked_orig_name, final_value)

		# Remove the consumed file
		if delete_stats_files:
			try:
				os.remove(input_dir+"/stats/"+file)
			except:
				pass

	print("All agent statistics files have been read")

	return 


################################################################################################
def print_matrix(matrix):
	num_cols=len(matrix[0])
	num_rows=len(matrix)
	for i in range(0,num_rows):
		print(matrix[i])


################################################################################################
#main program to execute by command line
#=======================================
print(" ")
print(" ")
print("Welcome to cloudbook stats monitor  (V1.0)")
print("=============================================")
print("This program analyzes statistics from agens and create consolidated filled matrix")
print("additionally this program recomends remake if detects high variations of matrix ")
print("  ")
print("usage:")
print(" py stats_monitor.py -project_folder <folder> -matrix <filematrix.json> [-t <seconds>]")
print("where: ")
print("   -project_folder : the name of the folder of your project")
print("   -matrix : the matrix to compare new stats")
print("   -t : (optional) stats monitoring interval. If not present, default value is 3/2*AGENT_STATS_INTERVAL")
print("   -no_remove_stats : (optional) only for debug purposes. this flag avoid deletion of agents stats files")
print("")



function_inverse_map={}
function_map={}


stats_interval=0 #initial value
filematrix="matrix.json"

delete_stats_files=True


# gather invocation parameters
# -----------------------------
num_param=len(sys.argv)
for i in range(1,len(sys.argv)):
	
	if sys.argv[i]=="-t":
		stats_interval=int(sys.argv[i+1])
		i=i+1

	if sys.argv[i]=="-matrix":
		filematrix=sys.argv[i+1]
		i=i+1

	if sys.argv[i]=="-project_folder":
		project_folder=	sys.argv[i+1]
		i=i+1

	if sys.argv[i]=="-no_remove_stats":
		delete_stats_files=False
		
	
if (project_folder==""):
	print("option -project_folder missing")
	sys.exit(0)


#load dictionary config.json to extract AGENT_STATS_INTERVAL
# ----------------------------------------------------------
if(platform.system()=="Windows"):
	path= os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']+os.sep+"cloudbook"+os.sep+project_folder	
else:
	path = os.environ['HOME'] + os.sep + "cloudbook" + os.sep + project_folder
	

input_dir = path + os.sep + "distributed"
config_dir = path + os.sep + "distributed"
config_dict = loader.load_dictionary(config_dir+ os.sep +"config.json")

agent_stats_interval=config_dict["AGENT_STATS_INTERVAL"]
print("  value of AGENT_STATS_INTERVAL at config.json is:",str(agent_stats_interval)," seconds")
# default value of stats interval is 3/2 * agent_stats_interval
if (stats_interval==0):
	stats_interval=(3*agent_stats_interval)/2

# check final value of stats_interval
if (stats_interval<agent_stats_interval):
	print("very low interval value (lower than AGENT_STATS_INTERVAL parameter at config.json")
	sys.exit(0)

if (stats_interval<5):
	print("very low interval value")
	sys.exit(0)

# read matrix input into a dictionary 
# this is the current cumulated stats file ( this is the filematrix) 
print(" Reading matrix: ", filematrix," ...")
matrix={}
matrix=loader.load_dictionary(input_dir+"/matrix/"+filematrix)
old_matrix=loader.load_dictionary(input_dir+"/matrix/"+filematrix)

print_matrix(matrix)

"""
print("matrix test invoker:move_tower, invoked:main:")
print(matrix_get("hanoi.move_tower", "hanoi.main"))
matrix_set("hanoi.move_tower","hanoi.main",23)
print(matrix_get("hanoi.move_tower", "hanoi.main"))
print("-----------")
print_matrix(matrix)
sys.exit(0)
"""

# ----------------- monitoring process --------------------------------	
while  True:
	print(timestamp(),"sleeping...", stats_interval, " seconds")
	print()
	time.sleep (float(stats_interval))
	print("============== STATS MONITOR ===============================")
	print(timestamp(), "End of sleep. Now ready for processing stats")

	#read function mapping file
	function_map=loader.load_dictionary(input_dir+"/matrix/function_mapping.json")
	print("functions mapping:")
	print(function_map)
	function_inverse_map={}
	for i in function_map:
		function_inverse_map[function_map[i]]=i

	
	print("--- current matrix ---")
	print_matrix(matrix)


	#for each agent stats
	#   read stats from agents and add their numbers to the matrix
	#   delete stats_xx.json
	get_stats(input_dir, delete_stats_files)
	
	print("--- new matrix ---")
	print_matrix(matrix)


	#write output file in json format
	#---------------------------------
	with open(input_dir+"/matrix/"+timestamp_file()+"_matrix.json", 'w') as fo:
		fo.write(json.dumps(matrix))


	# compare old stats with new stats
	recomendation=compare_matrix(old_matrix,matrix)
	print ("---------------------------------------")
	print("        RECOMENDATION REMAKE:", recomendation)
	print ("---------------------------------------")
	if recomendation:
		print ("stop the stats monitor before launch remake")
		print ("after remake you can launch stats monitor again") 
	#	sys.exit(0)

	# make a recomendation (REQUEST_REMAKE file) based on the comparison achieved




