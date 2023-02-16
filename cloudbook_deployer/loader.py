import json, ast
import time


def load_dictionary_old(filename, configuration = None):
	with open(filename, 'r') as file:
		aux = json.load(file)
	return aux


def load_dictionary(filename, configuration = None):
	success=False
	counter=0
	aux=None

	while (success==False and counter <10):
		with open(filename, 'r') as file:
			try:
				aux = json.load(file)
				if (aux!=None):
					success=True
				else:
					time.sleep(0.5)
			except:
				counter=counter+1
				file.close()
				success=False
				time.sleep(0.5) # 100 ms sleeping

	if (success):		
		return aux
	else:
		return None


def load_cloudbook(filename, configuration = None):
	with open(filename, "r") as file:
		txt = str(file.read())
		aux = dict(ast.literal_eval(txt))
		return aux