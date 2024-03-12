import logging
import os,sys
import platform
import json
import time
import threading
from datetime import datetime
#SKYNNET: COMENTADO POR COMPATIBILIDAD CON RADON
#from radon.visitors import ComplexityVisitor
#SKYNNET: Para permitir el demake
import shutil

from graph_analyzer import graph_analyzer
from splitter import splitter

##CONSTANTS
ERR_NO_PROJECT = "ERROR: Option -project_folder missing"
ERR_NO_CONFIG = "ERROR: Distributed/config.json not available, a general config.json will be created" #SKYNNET: esto deberia ser error? o warning?

def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, printEnd = "\r"):
	"""
	Call in a loop to create terminal progress bar
	@params:
		iteration   - Required  : current iteration (Int)
		total       - Required  : total iterations (Int)
		prefix      - Optional  : prefix string (Str)
		suffix      - Optional  : suffix string (Str)
		decimals    - Optional  : positive number of decimals in percent complete (Int)
		length  - Optional  : character length of bar (Int)
	"""
	str_format = "{0:." + str(decimals) + "f}"
	percents = str_format.format(100 * (iteration / float(total)))
	filled_length = int(round(length * iteration / float(total)))
	bar = '█' * filled_length + '-' * (length - filled_length)

	sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

	if iteration == total:
		sys.stdout.write('\n')
	sys.stdout.flush()

def indent_log(level):
	'''Auxiliar function to order the level of indentation in log'''
	filehandler = logging.FileHandler('./cloudbook_maker.log', 'a')
	if level==0:
		formatter = logging.Formatter('%(message)s')
	if level==1:
		formatter = logging.Formatter('	%(message)s')
	if level==2:
		formatter = logging.Formatter('		%(message)s')
	if level==3:
		formatter = logging.Formatter('			%(message)s')
	filehandler.setFormatter(formatter)
	log = logging.getLogger()  # root logger - Good to get it only once.
	for hdlr in log.handlers[:]:  # remove the existing file handlers
		if isinstance(hdlr,logging.FileHandler):
			log.removeHandler(hdlr)
	log.addHandler(filehandler)      # set the new handler


#Funcion propia de skynnet, feature secreta
def cloudbook_demake(project_path):
	'''Opcion secreta, borra todo del proyecto salvo original y agents'''
	response = input("El demake de un proyecto borra toda la carpeta distributed salvo el config, pulsa 1 para continuar")
	if response == "1":
		distributed_fs_path = project_path+os.sep+"distributed"
		#rescato el config, y borro todo, distributed incluido
		for file in os.listdir(distributed_fs_path):
			if file=="config.json":
				os.rename(distributed_fs_path+os.sep+file, project_path+os.sep+file)
		#borro distributed con todo lo que tiene
		shutil.rmtree(distributed_fs_path)
		print("Demake con exito")
		return True
	else:
		return False

################################# MAIN ########################################
def main():
	print (" ")
	print (" ")
	print ("Welcome to cloudbook maker")
	print ("==========================")
	print ("")
	print ("Usage")
	print ("python3 cloudbook_maker.py -project_folder <project_folder> [-matrix <filematrix.json>] [-log <debug|info|warning|error|critical|all>]")
	print ("    ")
	print ("    where:")
	print ("      -matrix filematrix.json is an optional parameter used for ")
	print ("                              remaking a program using new matrix values")
	print ("      -log level is an optional parameter used for show traces of the execution ")
	print ("                              by default the log is made in a file.")
	print ("   ")

	#Gather invocation parameters
	#============================
	project_folder = ""
	filematrix=None
	log_level = "file"
	demake = False #SKYNNET: para deshacer un proyecto, secreto, solo para tests
	num_param=len(sys.argv)
	for i in range(1,len(sys.argv)):
		if sys.argv[i]=="-matrix":
			filematrix=sys.argv[i+1]
			i=i+1
		if sys.argv[i]=="-project_folder":
			project_folder=	sys.argv[i+1]
			i=i+1
		if sys.argv[i]=="-log":
			log_level=	sys.argv[i+1]
			i=i+1
		if sys.argv[i]=="-demake":
			i=i+1
			demake = True

	#Assign value to invocation parameters
	#=====================================
	if log_level == "file":
		log_level = logging.DEBUG
		log_filename = 'cloudbook_maker.log'
		log_filemode = 'w'
		#log_datefmt = '%d-%b-%y %H:%M:%S'
		#log_format = '%(asctime)s - %(levelname)s - %(message)s'
		log_format = '%(message)s'
		#logging.basicConfig(level=log_level, filename=log_filename, filemode=log_filemode, format=log_format, datefmt='%d-%b-%y %H:%M:%S')
		logging.basicConfig(level=log_level, filename=log_filename, filemode=log_filemode, format=log_format)
	else:
		if (log_level == "debug") or (log_level == "all"): log_level = logging.DEBUG
		elif log_level == "info": log_level = logging.INFO
		elif log_level == "warning": log_level = logging.WARNING
		elif log_level == "error": log_level = logging.ERROR
		elif (log_level == "critical"): log_level = logging.CRITICAL
		#log_format = '%(asctime)s - %(levelname)s - %(message)s'
		#log_datefmt = '%d-%b-%y %H:%M:%S'
		#logging.basicConfig(level=log_level, format=log_format, datefmt='%d-%b-%y %H:%M:%S')
		log_format = '%(message)s'
		logging.basicConfig(level=log_level, format=log_format)

	if (project_folder==""):
		logging.error(ERR_NO_PROJECT)
		raise ValueError(ERR_NO_PROJECT)

	if(platform.system()=="Windows"):
		path = os.environ['HOMEDRIVE'] + os.environ['HOMEPATH']+ os.sep + "cloudbook"
		if not os.path.exists(path):
			os.makedirs(path)
	else:
		path = os.environ['HOME'] + os.sep + "cloudbook"
		if not os.path.exists(path):
			os.makedirs(path)

	project_path = path+os.sep+project_folder 
	distributed_fs_path = project_path+os.sep+"distributed" 
	agents_fs_path = project_path+os.sep+"agents"  #SKYNNET

	#SKYNNET: Si se ha metido la opcion secreta demake, se llama a la funcion
	if (demake):
		if cloudbook_demake(project_path):
			return 0
		else:
			print("Error al hacer demake, hazlo de manera manual")
			return 0

	input_matrix = ""
	if filematrix != None:
		filename = project_path+os.sep+"distributed"+os.sep+"matrix"+os.sep+filematrix
		if filename.find(".json") == -1:
			filename = filename+".json"
		with open(filename, 'r') as file:
			aux = json.load(file)
			file.close()
		input_matrix = aux
	logging.debug(input_matrix)

	#Creation of needed subfolders
	#=============================
	if not os.path.exists(distributed_fs_path):
		os.makedirs(distributed_fs_path)
	if not os.path.exists(distributed_fs_path+os.sep+"stats"):
		os.makedirs(distributed_fs_path+os.sep+"stats")
	if not os.path.exists(distributed_fs_path+os.sep+"du_files"):
		os.makedirs(distributed_fs_path+os.sep+"du_files")
	if not os.path.exists(distributed_fs_path+os.sep+"matrix"):
		os.makedirs(distributed_fs_path+os.sep+"matrix")
	if not os.path.exists(distributed_fs_path+os.sep+"agents_grant"):
		os.makedirs(distributed_fs_path+os.sep+"agents_grant")
	if not os.path.exists(distributed_fs_path+os.sep+"working_dir"):
		os.makedirs(distributed_fs_path+os.sep+"working_dir")
	#SKYNNET
	if not os.path.exists(agents_fs_path):
		os.makedirs(agents_fs_path)

	#Read config.json and creates it for this execution
	#==================================================  
	#SKYNNET TODO: Reducir esta parte del codigo, ya no es try except, es un if (hacer si se aprueba)
	config_file = distributed_fs_path+os.sep+"config.json"
	try:
		with open(config_file, 'r') as file:
				config_input = json.load(file)
	except Exception as e:
		logging.error(ERR_NO_CONFIG)
		#SKYNNET: Si esta en la raiz, no creo el nuevo
		if os.path.exists(project_path+os.sep+"config.json"):
			os.rename(project_path+os.sep+"config.json", distributed_fs_path+os.sep+"config.json")
		else: #lo creo
		#SKYNNET: Si no existe config file lo creo por defecto y lo meto en distribute
			config_content = {
	  "NAME": project_folder,
	  "DESCRIPTION": "Config file created automatically",
	  "NUM_DESIRED_AGENTS": 2,
	  "AGENT_GRANT_INTERVAL": 5,
	  "AGENT_STATS_INTERVAL": 5,
	  "LAN": True,
	  "CLOUDBOOK_MAXTHREADS": 0,	
	  "NON-RELIABLE_AGENT_MODE": True, 
	  "AGENT0_ONLY_DU0":True	
	}
			with open(config_file, 'w') as file:
				json.dump(config_content,file)
		#SKYNNET: El config file esta creado o movido correctamente
		with open(config_file, 'r') as file:
				config_input = json.load(file)	
		#raise e #SKYNNET: Ya no es un error, he generado otro config nuevo

	#SKYNNET: Make easy, compruebo si existe la carpeta agents y original, si no existe, voy a la funcion make easy y creo todo.
	source_fs_path = project_path+os.sep+"original"
	if not os.path.exists(source_fs_path):
		os.makedirs(source_fs_path)
		#SKYNNET: Buscar ficheros python y meterlos en source
		for file in os.listdir(project_path):
			if file.endswith(".py"):
				os.rename(project_path+os.sep+file, source_fs_path+os.sep+file)
			
	#Generates de config dict for the maker process
	config_dict = {
				"input_dir": project_path + os.sep + "original",
				"output_dir": distributed_fs_path + os.sep + "du_files",
				"distributed_dir": distributed_fs_path,
				"program_files": None,
				"function_list": None,
				"function_translated": {},
				"class_list": None,			
				"matrix": None,	
				"input_matrix": input_matrix,		
				"num_dus": config_input["NUM_DESIRED_AGENTS"],
				"dus": {},
				"pragmas":{},
				"global_vars": {},
				"imports": {},
				"critical_dus" : [],
				"max_threads": config_input["CLOUDBOOK_MAXTHREADS"],
				"non-reliable_agent_mode": config_input["NON-RELIABLE_AGENT_MODE"],
				"agent0_only_du0": config_input["AGENT0_ONLY_DU0"],
				"program_data": {},
				"program_index": {},
				"nonblocking_invocations":{},
				"nonblocking_inv_nodes":{},
				"log_file_handler": logging.FileHandler('./cloudbook_maker.log', 'a')
				} 

	#Init the maker
	start_time = time.time()
	logging.info("Cloudbbok Maker started:")
	logging.info("=======================================")
	logging.info("Starting time %s", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
	logging.info("Config_dict created, ready for start the maker process.")
	logging.debug("Config_dict (relevant info):")
	logging.debug("	%s	%s","input_dir:              ",config_dict["input_dir"])
	logging.debug("	%s	%s","output_dir:             ",config_dict["output_dir"])
	logging.debug("	%s	%s","num_dus:                ",config_dict["num_dus"])
	logging.debug("	%s	%s","non-reliable_agent_mode:",config_dict["non-reliable_agent_mode"])
	logging.info("Init complete")
	logging.info("=======================================")

	indent_log(1)
	#Start the process: Graph Analyzer
	printProgressBar(0, 4, prefix = 'Building graph                       :', suffix = 'Complete', length = 50)#, printEnd='\r')
	graph_analyzer.graph_builder(config_dict)
	time.sleep(0.5)

	printProgressBar(1, 4, prefix = 'Filling graph                        :', suffix = 'Complete', length = 50, printEnd='\r')
	graph_analyzer.graph_filler(config_dict)
	time.sleep(0.5)

	indent_log(0)
	logging.info("=====================================")
	indent_log(1)
	#Go to the splitter
	printProgressBar(2, 4, prefix = 'Splitting program and writing dus    :', suffix = 'Complete', length = 50, printEnd='\r')
	splitter.split_program(config_dict)
	time.sleep(0.5)

	printProgressBar(3, 4, prefix = 'Getting complexity and critical dus  :', suffix = 'Complete', length = 50, printEnd='\r')
	time.sleep(0.5)


	###############Save function translated into funciton mapping
	out_route =  distributed_fs_path + os.sep + "matrix" + os.sep + "function_mapping.json"
	file = open(out_route,"w")
	translated_str = json.dumps(config_dict["function_translated"])
	file.write(translated_str)
	file.close()

	###############Create du_list and critical_dus
	indent_log(0)
	logging.info(config_dict["dus"])
	logging.info(config_dict["critical_dus"])
	du_list = []
	du_dict = {}
	for i in config_dict["dus"].keys():
		du_list.append(i)
	#SKYNNET: COMENTADA ESTA PARTE PORQUE ES EL CALCULO DE COMPLEJIDAD CON RADON
	#WARNING: LOS CAMPOS COST Y SIZE DEL DICCIONARIO NO LOS RELLENO, PUEDE DAR PROBLEMAS EN EL FUTURO, SI LOS DA, RELLENAR AQUI DIRECTAMENTE CON 0.
	#	BUCLE COMO EL SIGUIENTE PONIENDO 0s O LO QUE SEA EN COST Y SIZE
	for i in range(len(du_list)): #SKYNNET BUCLE "DE PEGA" PARA RELENAR VALORES COST Y SIZE
		du_name = du_list[i]
		du_dict[du_name]={}
		#SKYNNET: Los nuevos costes por ahora serán: "size" ->lineas de codigo "cost"->lineas de codigo, pero si estan en un bucle se multipican por el numero de veces que se ejecuta el bucle
		du_dict[du_name]["cost"]=20
		du_dict[du_name]["size"]=20
	'''for i in range(len(du_list)):
		du_name = du_list[i]
		out_route = config_dict["output_dir"]+os.sep+du_name+".py"
		##print (out_route)
		cadena = ""
		file = open(out_route,"r")
		for i in file:
			cadena = cadena + i
		try: 
			v = ComplexityVisitor.from_code(cadena)
		except TabError:
			raise TabError("Error in indentation of dus, please indent source code with divisible by 4 spaces or tab size")
		#print(v.functions)
		temp_complex = 0
		temp_size = 0
		for i in v.functions:
			#print(i.fullname,i.complexity,i.endline-i.lineno)
			temp_complex += i.complexity
			temp_size += i.endline-i.lineno
		du_dict[du_name]={}
		du_dict[du_name]["cost"]=temp_complex
		du_dict[du_name]["size"]=temp_size'''
		#para el size resto lineas y punto
	##print(du_dict)
		
	json_str = json.dumps(du_dict)
	#fo = open("./du_list.json", 'w')
	du_list_route = distributed_fs_path+os.sep+"du_list.json"
	fo = open(du_list_route, 'w')
	fo.write(json_str)
	fo.close()

	logging.info(config_dict["critical_dus"])
	critical_dus_route = distributed_fs_path+os.sep+"critical_dus.json"
	critical_dus_dict = {}
	#put du0 in critical dus
	if "du_0" not in config_dict["critical_dus"]:
		config_dict["critical_dus"].append("du_0")
	if len(config_dict["critical_dus"]) != 0:
		fo = open(critical_dus_route, 'w')
		#fo.write(str(config_dict["critical_dus"]))
		critical_dus_dict["critical_dus"] = config_dict["critical_dus"]
		json_str = json.dumps(critical_dus_dict)
		fo.write(json_str)
		fo.close()
	##print("critical_dus file written", critical_dus_dict)

	#print("Process complete", end='\r')
	printProgressBar(4, 4, prefix = 'Process complete                   :', suffix = 'Completed', length = 50, printEnd='\r')

	end_time = time.time()
	logging.info("=======================================")
	logging.info("Cloudbook Maker completed in %s",end_time-start_time)
	logging.info("Ending time %s", datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

if __name__=="__main__":
	main()