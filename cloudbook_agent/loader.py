#####   IMPORTS   #####
import json
import time
from pathlib import Path



#####   FUNCTIONS   #####

# Returns a function that acts as a decorator. Decorator returns the result of the decorated function after trying up to max_retries times if Exceptions raise.
# Re-raises the exception after max_retries is reached
def retry(max_retries):
	def retry_decorator(func):
		def wrapper(*args, **kwargs):
			retries = 0
			while True:
				try:
					return func(*args, **kwargs)
				except Exception as e:
					if retries<=max_retries:
						print("ERROR reading or writing file. Retries:", retries)
						print(str(type(e).__name__) + ": " + str(e))
						retry_backoff = max(0.1, 0.1*retries)
						retry_backoff = min(retry_backoff, 0.5)
						time.sleep(retry_backoff)
						print("\nRetrying...")
					else:
						raise e
				retries += 1
		return wrapper
	return retry_decorator


# Returns the list of dus for the specified agent given the cloudbook dictionary
def load_cloudbook_agent_dus(my_agent_ID, cloudbook_dict_agents, configuration = None):
	du_list = []
	for du in cloudbook_dict_agents:
		for agent in cloudbook_dict_agents[du]:
			if agent==my_agent_ID:
				du_list.append(du)
	return du_list


# Returns a dictionary loaded from a json file
@retry(max_retries=3)
def load_dictionary(filename, configuration = None):
	with open(filename, 'r') as file:
		aux = json.load(file)
	return aux


# Writes a dictionary into a json file
@retry(max_retries=10)
def write_dictionary(data, filename, configuration = None):
	with open(filename, 'w') as file:
		json_data = json.dumps(data)
		file.write(json_data)


# Creates a file without content if it does not exist
@retry(max_retries=10)
def touch(filename):
	Path(filename).touch(exist_ok=True)
