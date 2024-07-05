
from . import sk_extra_codes
from ast import *
import sys
import os
import re
from ast_comments import *
from math import comb,ceil
import glob


#Variables globales
sk_vars_list = ["_EMBEDDING_","_NEURON_","_CELL_","_EPOCHS","_FILTERS_"]
sk_functions_list = ['summary','compile','fit','predict',]
sk_creation_model_list = ['Sequential','Model']

debug_option = 1
num_subredes = 0

def debug(msj):
    if debug_option==1:
        print("DEBUG: ",msj)

def tab_indent(file):
    # Leer el contenido del archivo
    with open(file, 'r') as archivo:
        lineas = archivo.readlines()

    # Reemplazar espacios por tabuladores
    for i in range(len(lineas)):
        # Contar espacios al inicio de la línea
        espacios = 0
        for char in lineas[i]:
            if char == ' ':
                espacios += 1
            else:
                break
        # Reemplazar espacios por tabuladores
        lineas[i] = '\t' * (espacios // 4) + '\t' * (espacios % 4) + lineas[i][espacios:]

    # Escribir el contenido modificado de vuelta al archivo
    with open(file, 'w') as archivo:
        archivo.writelines(lineas)

    #print("Indentación convertida a tabuladores.")

def get_var_from_list(cadena, lista):
    '''Esta funcion se usa para reconocer las variables especificas para capas de neuronas que pedimos que ponga el diseñador
    Esta funcion recibe un string de una variable y una lista de variables
    comprueba si las variable pertenece a la cadena, como a veces la variable
    incluye un _numero para indicar el numero de la capa en la que esta, primero lo separa, para asegurar que la variable sin numero es una de las de la lista que nos interesan

    Devuelve una tupla (terna): 
    - True o False: Si la variable es de las de la lista
    - El nombre de la variable sin el numero
    - El numero de la variable, que puede ser:
        - n, un numero entero
        - 0, si la variable no tiene numero
        - -1 si la variable no era de la lista
    '''
    #Separo el numero con er y tengo var y numero (si hay)
    hay_num = re.search(r'\d+',cadena) 
    if hay_num:
        start_num = hay_num.start()
        end_num = hay_num.end()
        sk_var = cadena[:start_num]
        num = cadena[start_num:end_num]
        if sk_var in lista:
            return True,sk_var,int(num)
        else:
            return False,sk_var,int(num)
    else:
        sk_var = cadena
        if sk_var in lista:
            return True,sk_var,0
        else:
            return False,sk_var,-1

class VisitAssignSkVars(NodeVisitor):
    def __init__(self,reduccion=1):
        self.reduccion = reduccion #Indica por cuanto hay que dividir el valor de la asignacion
        self.permiso = True #Si el permiso es false, no se deconstruye porque queda demasiado pequeño

    def visit_Assign(self,node):
        global sk_vars_list
        if len(node.targets)==1:
            variable_valida =  isinstance(node.targets[0], ast.Name) and node.value
            if variable_valida:
                testing_variable = get_var_from_list(node.targets[0].id, sk_vars_list)
                variable_skynnet = testing_variable[0]==True
                variable_skynnet_name = testing_variable[1]
                if variable_valida and variable_skynnet:
                    #new_value = ceil(node.value.value/self.reduccion)
                    new_value = node.value.value/self.reduccion
                    if variable_skynnet_name == '_FILTERS_' and new_value<2:
                        #print(f"WARNING: Reducing the filters variable would make make the last layer with filters smaller than two, so IT WILL NOT DECONSTRUCT THE LAYERS WITH FILTERS.  Check the source code to deconstruct it. ")
                        print(f"ERROR: La variable _FILTERS_{testing_variable[2]} va a ser {new_value}, menor que 2, por lo que no se va a deconstruir"
                            "\n\tHaz la capa mas grande o divide en menos subredes, operacion abortada."
                            )
                        sys.exit()
                        self.permiso = False                        
                        sk_vars_list.remove("_FILTERS_")

class TransformAssignSkVars(ast.NodeTransformer):
    '''Esta clase es la que se usa para detectar de forma automatica las variables de las 
    redes neuronales y reducir el valor que se les da para adecuarlas a las respectivas subredes
    por ejemplo: _NEURON_3 = 100 ------->  _NEURON_3 = 50, si se divide en dos subredes'''

    def __init__(self,reduccion=1):
        self.reduccion = reduccion #Indica por cuanto hay que dividir el valor de la asignacion
        self.permiso = True #Si el permiso es false, no se deconstruye porque queda demasiado pequeño

    def visit_Assign(self, node):
        '''Esta funcion es la que divide por un numero entero las variables de skynnet
        '''
        if len(node.targets)==1:
            variable_valida =  isinstance(node.targets[0], ast.Name) and node.value
            if variable_valida:
                testing_variable = get_var_from_list(node.targets[0].id, sk_vars_list)
                variable_skynnet = testing_variable[0]==True
                variable_skynnet_name = testing_variable[1]
                if variable_valida and variable_skynnet:
                    new_value = ast.Constant(value=(ceil(node.value.value/self.reduccion)))
                    new_value_permission = ast.Constant(value=(node.value.value/self.reduccion))
                    #print(f"La variable {variable_skynnet_name} se queda en {new_value.value} por que la reduccion es {node.value.value}/{self.reduccion}")
                    if new_value_permission.value <2 and variable_skynnet_name != '_EPOCHS':
                        print(f"ERROR: La variable {node.targets[0].id} se va a reducir a {new_value_permission.value}, menor que 2, por lo que no se va a deconstruir"
                        "\n\tHaz la capa mas grande o divide en menos subredes, operacion abortada."
                            )
                        sys.exit()
                        new_value.value = 2
                        self.permiso = False
                    
                    new_node = ast.Assign(targets=node.targets, value=new_value, lineno = node.lineno)
                    return new_node
                else:
                    # Si no es una asignación de un solo objetivo con un valor, simplemente devuelve el nodo original sin modificarlo
                    #print("Nodo erroneo", node.targets[0].id)
                    return node
            else:
                return node
        else:
            return node

class VisitModelFunctions(ast.NodeVisitor):
    '''Esta clase es la que permite obtener las asignaciones que se usan para crear modelos en skynnet,
    ya sea con el modelo secuencial o funcional. Ademas prepara el diccionario que tendra un resumen de los nodos
    para las funciones summary, creation, compile, fit, si añadimos alguna funcion nueva se añade al diccionario de forma automatica en otra clase'''

    def __init__(self):
        self.dict_modelo = {}

    @staticmethod
    def get_sk_model_creation(llamada):
        for function in sk_creation_model_list:
            if function in llamada:
                return True
            else:
                continue
        return False


    def visit_Assign(self,node):
        #nodo valido un nombre igual a una invocacion
        nodo_valido_izqda = len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        nodo_valido_dcha = isinstance(node.value, ast.Call)
        if nodo_valido_izqda and nodo_valido_dcha:
            llamada = node.value
            if self.get_sk_model_creation(ast.unparse(llamada)):
                model_name = node.targets[0].id
                self.dict_modelo = {'name': model_name, 'creation': node}
                #self.dict_modelo[model_name] = {'creation': node }
            self.generic_visit(node)

    
    def visit_Call(self,node):#funciones tipo model.fit(lo que sea)
        #nodo valido, si node.func es un atributo (de model)
        #y esta en la lista de funciones que queremos para skynnet
        if isinstance(node.func, ast.Attribute) and node.func.attr in sk_functions_list:
            #print(self.dict_modelo)
            if isinstance(node.func.value, ast.Name) and node.func.value.id == self.dict_modelo['name']:#.keys():
                #self.dict_modelo[node.func.value.id][node.func.attr] = node
                self.dict_modelo[node.func.attr] = node
                #print(f"A ver q pasa {unparse(node)}")
        
        self.generic_visit(node)

class getInputModel(ast.NodeVisitor):
    '''meto en el dict, el input del diccionario, para tener el nodo en el que insertar division de datos
    OJO: busca una invocacion a input de tensor flow, no debería haber otro input de otro modulo'''
    def __init__(self,dict_modelo):
        self.dict_modelo = dict_modelo
        #self.model_name = model_name
        #self.dict_modelos[self.model_name] = {}
    
    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "Input":
                #self.dict_modelos[self.model_name]["input"] = node
                self.dict_modelo["input"] = node
        
        self.generic_visit(node)

class RemovePredictionNode(ast.NodeTransformer):
    '''Elimino la asignacion predicted = model.predict(x), solo las que tengan esa
    forma especifica, si no la tiene, se puede asumir que no la va a usar? asegurar que la haga de esta forma'''

    def __init__(self,dict_modelo):
        self.dict_modelo = dict_modelo
        self.predict_nombre = ""
        self.removed =  False
        self.lista_nodos_post_predict = []
    
    def visit(self, node):
        if isinstance(node, ast.Assign):
            nodo_valido_izqda = len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
            nodo_valido_dcha = isinstance(node.value, ast.Call)

            if nodo_valido_izqda and nodo_valido_dcha:
                derecha = node.value
                if (
                    isinstance(derecha.func, ast.Attribute)
                    and derecha.func.attr == 'predict'
                    and isinstance(derecha.func.value, ast.Name)
                    and derecha.func.value.id == self.dict_modelo['name']#in self.dict_modelos.keys()
                ):
                    self.predict_nombre = unparse(node.targets[0])
                    self.removed = True
                    return None
                elif self.removed:
                    self.lista_nodos_post_predict.append(node)
                    return None
                else:
                    return node
            elif self.removed:
                self.lista_nodos_post_predict.append(node)
                return None
            else:
                return node
        elif self.removed:
            self.lista_nodos_post_predict.append(node)
            return None

        self.generic_visit(node)
        return node

class ModelArrayTransform(ast.NodeTransformer):
    '''Esta clase es para cambiar los modelos por arrays de modelos, 
    cambia todas las apariciones del modelo'''
    def __init__(self, model_name):
        self.model_name = model_name

    def visit_Name(self, node):
        if node.id == self.model_name:
            return ast.Subscript(
                value=ast.Name(id= self.model_name, ctx=ast.Load()),
                slice=ast.Index(value=ast.Name(id='sk_i', ctx=ast.Load())),
                ctx=node.ctx
            )       
        return node#self.generic_visit(node)

class VisitLastNeuron(ast.NodeVisitor):
    '''Esta clase es para obtener el numero de categorias en las que se clasifica
    Si la asignacion es valida ("variable=valor")
    Obtiene sus parametros (el nombre y el numero, para poder elegir la mas alta "_NEURON_3")
    La variable last_neuron contiene el nombre y el numero de categorias'''
    max_valor = 0
    n_categorias = 0
    last_neuron = ('NEURON_X',0)

    def visit_Assign(self, node):
        '''Esta funcion es la que divide por un numero entero las variables de skynnet
        '''
        variable_valida =  (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.value)
        if variable_valida:
            existe_sk_var,variable_skynnet,valor = get_var_from_list(node.targets[0].id, sk_vars_list)          
            if existe_sk_var == True and variable_skynnet == '_NEURON_':
                #print(f"node.value es {node.value.value}")
                if valor>self.max_valor:
                    self.last_neuron = ()
                    self.max_valor = valor
                    self.n_categorias = node.value.value
                    self.last_neuron = (node.targets[0].id,self.n_categorias)

class GetModelDataVars(ast.NodeVisitor):
    '''Uso esta clase para guardar en el diccionario las variables de datos del modelo'''
    data_vars_train = ["_DATA_TRAIN_X","_DATA_TRAIN_Y"]
    data_vars_val = ["_DATA_VAL_X","_DATA_VAL_Y"]
    data_vars_test = ["_DATA_TEST_X","_DATA_TEST_Y"]
    data_vars_train_gen = {"_DATA_TRAIN_GEN_X","_DATA_TRAIN_GEN_Y"}

    #def __init__(self,model_name, dict_modelo):
    def __init__(self, dict_modelo):
        self.dict_modelo = dict_modelo
        self.dict_modelo["data_train"] = []
        self.dict_modelo["data_val"] = []
        self.dict_modelo["data_test"] = []
        self.dict_modelo["data_gen_train"] = [] #data generator for training

    def visit_Assign(self,node):
        try:
            if len(node.targets)==1 and node.targets[0].id in self.data_vars_train:
                self.dict_modelo["data_train"].append(node)
            if len(node.targets)==1 and node.targets[0].id in self.data_vars_val:
                self.dict_modelo["data_val"].append(node)
            if len(node.targets)==1 and node.targets[0].id in self.data_vars_test:
                self.dict_modelo["data_test"].append(node)
            if len(node.targets)==1 and node.targets[0].id in self.data_vars_train_gen:
                self.dict_modelo["data_gen_train"].append(node)
        except:
            pass

# Clase de visitante para buscar definiciones de función y agregar nonlocal
class NonlocalAdder(ast.NodeTransformer):

    data_vars_train = ["_DATA_TRAIN_X","_DATA_TRAIN_Y"]
    data_vars_val = ["_DATA_VAL_X","_DATA_VAL_Y"]
    data_vars_test = ["_DATA_TEST_X","_DATA_TEST_Y"]

    def __init__(self,dict_modelo,tipo_fun):
        self.dict_modelo = dict_modelo
        self.tipo_fun = tipo_fun #Tipo de la funcion principal, la que visitas es interna


    def visit_FunctionDef(self, node):
        if 'skynnet_train' not in node.name:
            if self.tipo_fun=='train':
                if self.dict_modelo['data_train'] != []:
                    node.body.insert(0,ast.Nonlocal(names=self.data_vars_train))
                if self.dict_modelo['data_val'] != []:
                    node.body.insert(0,ast.Nonlocal(names=self.data_vars_val))
            #TODO si hace falta en el predict
            #elif tipo_fun=='predict':
            self.generic_visit(node)
            return node
        self.generic_visit(node)
        return node

#Clase para cambiar los load y saves
class ModifyPaths(ast.NodeTransformer):

    def __init__(self,dict_modelo):
        self.dict_modelo = dict_modelo

    '''def visit_Assign(seld,node):
        if isinstance(node.value,ast.Call):
            llamada=node.value
            if isinstance(llamada.func, ast.Attribute) and hasattr(llamada.func,'value'):
                if isinstance(llamada.func.value, ast.Name):
                    if (llamada.func.value.id == "tf") and (llamada.func.attr == "keras"):
                        print("HOLA")'''

    def visit_Call(self, node):
        # Comprueba si es una llamada a `save` o `load`
        if isinstance(node.func, ast.Attribute) and hasattr(node.func,'value'):
            if isinstance(node.func.value, ast.Name):
                if (node.func.value.id == self.dict_modelo['name']):
                    if node.func.attr == "save":
                        #Insertamos antes del h5 el indice
                        parts = node.args[0].s.split('.')#separo la ruta por el punto
                        #node.args[0] = parse(f"'{parts[0]}'+str(sk_i)+'.{parts[1]}'")
                        new_args = parse(f"'{parts[0]}'+str(sk_i)+'.{parts[1]}'")
                        node.args = [new_args]
                        fix_missing_locations(node)
        if isinstance(node.func, ast.Attribute) and hasattr(node.func,'attr'):
            if node.func.attr == "load_model":
                parts = node.args[0].s.split('.')#separo la ruta por el punto
                node.args[0] = parse(f"'{parts[0]}'+str(sk_i)+'.{parts[1]}'")
                fix_missing_locations(node)            
        self.generic_visit(node)
        return node

class NodeRemover(ast.NodeTransformer):
    def __init__(self, target_node):
        self.target_node = target_node

    def visit(self, node):
        # Si el nodo es del tipo que queremos eliminar, devolver None lo elimina
        #if isinstance(node, self.target_node_type):
        if node==self.target_node:
            return None
        return self.generic_visit(node)

def generator_datos_train_fit(categorias,grupos,last_neuron,tipo_red):
    datos_y = "_DATA_TRAIN_GEN_Y"
    division_datos_gen = sk_extra_codes.division_datos_gen_fit(categorias,grupos,last_neuron,tipo_red,datos_y)
    return fix_missing_locations(parse(division_datos_gen))


def get_data_type(tipo_datos):
    if tipo_datos == "train":
        datos_x = "_DATA_TRAIN_X"
        datos_y = "_DATA_TRAIN_Y"
    elif tipo_datos== "validate":
        datos_x = "_DATA_VAL_X"
        datos_y = "_DATA_VAL_Y"
    elif tipo_datos == "test":
        datos_x = "_DATA_TEST_X"
        datos_y = "_DATA_TEST_Y"
    else:
        print("Warning unknown data type")
        return None,None
    return datos_x,datos_y

def division_datos_fit(tipo_datos,categorias,grupos,last_neuron,tipo_red):
    #Determinar tipo de datos que se usa
    datos_x,datos_y = get_data_type(tipo_datos)
    if (datos_x,datos_y) != (None,None):
        #Generar codigo para la division de datos en tiempo real
        if tipo_red == 'MULTICLASS':
            division_datos = sk_extra_codes.division_datos_fit_multiclass(categorias, grupos, datos_x,datos_y,last_neuron)
        elif tipo_red == 'BINARYCLASS':
            division_datos = sk_extra_codes.division_datos_fit_binaryclass(tipo_datos,datos_x,datos_y,last_neuron)
        elif tipo_red == 'REGRESSION':
            division_datos = sk_extra_codes.division_datos_fit_regression(grupos,tipo_datos,datos_y, last_neuron)
        return fix_missing_locations(parse(division_datos))
    else:
        print("Error with training data")
        return None

def preparacion_datos_predict(tipo_datos,categorias,grupos,last_neuron,tipo_red,model_name,medida_compuesta, predict_name):
    '''Ya no es division de datos, es la adaptacion del predict para sacar el compuesto
    Medida compuesta puede ser: "acc", "loss","acc,loss"'''
    datos_x,datos_y = get_data_type(tipo_datos)
    if (datos_x,datos_y) != (None,None):
        if tipo_red == 'MULTICLASS':
            division_datos = sk_extra_codes.preparacion_datos_predict_multiclass(medida_compuesta,predict_name,model_name,datos_y,categorias,grupos)
        elif tipo_red == 'BINARYCLASS':
            division_datos = sk_extra_codes.preparacion_datos_predict_binaryclass(medida_compuesta,predict_name,categorias,model_name)
        elif tipo_red == 'REGRESSION':
            division_datos = sk_extra_codes.preparacion_datos_predict_regression(predict_name,model_name,categorias)
        return fix_missing_locations(parse(division_datos))
    else:
        print("Error with predict data")
        return None

def inserta_nodo(sk_dict,model_name,to_insert_node,node_destiny,last_neuron):
    
    nodo_a_buscar = sk_dict["creation"]
    nodo_a_buscar = sk_dict["input"]
    if isinstance(node_destiny, ast.AST):
        for child in ast.iter_child_nodes(node_destiny):
            #print("child node es", child)
            if child == nodo_a_buscar:
                #print(f"ENCONTRADO en {unparse(child)}")
                index = node_destiny.body.index(child)
                node_destiny.body.insert(index, to_insert_node)
                #print("Nodo insertado")
                break
            else:
                inserta_nodo(sk_dict, model_name, to_insert_node, child,last_neuron)
    elif isinstance(node_destiny, list):
        for child in node_destiny:
            inserta_nodo(sk_dict, model_name, to_insert_node, child,last_neuron)

def inserta_filtro_datos(nodo_destino,tipo_funcion,sk_dict,categorias,grupos,last_neuron,tipo_red, medida_compuesta, predict_name):
    '''tipo funcion: general(train y val) predict(test), general es la division para entrenar
    nodo_destino: nodo tipo funcion en el que hay que insertar'''
    model_name = sk_dict['name']
    if tipo_funcion=="general":
        if sk_dict["data_gen_train"] != []:
            to_insert_node = generator_datos_train_fit(categorias,grupos,last_neuron,tipo_red)
            inserta_nodo(sk_dict,model_name,to_insert_node,nodo_destino,last_neuron)
        if sk_dict["data_train"] != []:
            to_insert_node = division_datos_fit("train",categorias,grupos,last_neuron,tipo_red)
            inserta_nodo(sk_dict,model_name,to_insert_node,nodo_destino,last_neuron)
        if sk_dict["data_val"] != []:
            to_insert_node = division_datos_fit("validate",categorias,grupos,last_neuron,tipo_red)
            inserta_nodo(sk_dict,model_name,to_insert_node,nodo_destino,last_neuron)
    elif tipo_funcion == "predict":
        if sk_dict["data_test"] != []:
            to_insert_node = preparacion_datos_predict("test",categorias,grupos,last_neuron,tipo_red,model_name, medida_compuesta, predict_name)
            nodo_destino.body.insert(8,to_insert_node) #En el predict es distinto, se exactamente donde insertar
    else:
        print(f"Error: el tipo de funcion no es valido ({tipo_funcion})")
                            
def create_new_file(file):
    '''Esta funcion, crea el fichero que vamos a devolver con la herramient sk_tool
    Es un fichero con el mismo nombre pero precedido de "sk_"'''
    if file.find(".py") == -1:
        sk_file = "output/sk_"+file+".py"
    else:
        sk_file = "output/sk_"+file
    open(sk_file, "w").close() #python deberia cerrarlo automaticamente, pero queda mas claro asi
    return sk_file

def get_skynnet_atributes(cadena):
    '''Esta funcion crea un diccionario que analiza la etiqueta de Skynnet
    y almacena el tipo de red y las opciones que permite, para luego calcular la
    reduccion de capas en cada caso'''
    skynnet_config = {}
    t_skynnet =r'(#)?(SKYNNET:BEGIN_)?(REGRESSION|MULTICLASS|BINARYCLASS)?(_ACC|_LOSS|_ACC_LOSS)?$'
    coincidencias = re.findall(t_skynnet,cadena)
    if len(coincidencias)==0:
        return skynnet_config
    coincidencias = list(coincidencias[0])
    nparams_correcto = (len(coincidencias)== 4 or len(coincidencias)==3)
    sk_begin_correcto = (coincidencias[0] == '#' and coincidencias[1] == 'SKYNNET:BEGIN_')
    if nparams_correcto and sk_begin_correcto:
        skynnet_config['Type'] = coincidencias[2]
        skynnet_config['Options'] = coincidencias[3] if len(coincidencias)==4 else ''
    return skynnet_config

def prepare_sk_file(file):
    ''' Esta funcion coge el fichero fuente, y apunta los indices de inicio y fin de 
    todas las parejas de etiquetas skynnet, ademas de guardar todo el codigo fente
    de skynnet que habrá que duplicar 
    Se almacena:
    -El codigo de inicio (antes de la etiqueta)
    -El codigo de skynnet (entre etiquetas)
    -El codigo de finalizacion (despues de la etiqueta end)

    Se permite que haya varias parejas de etiquetas skynnet, por eso los codigos de skynnet y finalizacion
    son listas
    '''

    sk_trees = []
    sk_tree = ""
    save_sk_code = False
    init_code = ""
    post_sk_codes = []
    post_sk_code = ""
    save_init_code = True
    save_post_sk_code = False
    skynnet_configs = []
    #file = "input/"+file

    with open(file,'r') as fi:
        line = fi.readline()
        i = 1
        while line:
            #print(line)
            if save_init_code:
                init_code+=line
            if save_sk_code:
                sk_tree+=line
            if save_post_sk_code:
                post_sk_code+=line
            if "SKYNNET:BEGIN" in line:
                skynnet_configs.append(get_skynnet_atributes(line))
                save_init_code = False
                save_post_sk_code = False
                save_sk_code = True
                start_skynnet = i
                if len(sk_trees) != 0:#Antes del primer begin, no hay post_sk_code 
                    post_sk_codes.append(post_sk_code)
                post_sk_code = ""
            if "SKYNNET:END" in line:
                save_init_code = False #Por si alguien lo pone desordenado o le falta etiqueta begin
                save_sk_code = False 
                end_skynnet = i
                sk_trees.append(sk_tree)
                sk_tree = ""
                save_post_sk_code = True
                post_sk_code = '\n'+line #La linea del end la tienen sk_code, y post_sk, porque sk_code la ignora y quiero conservarla      
            i+=1
            line = fi.readline()
        post_sk_codes.append(post_sk_code)

    return(sk_trees,init_code,post_sk_codes,skynnet_configs)

def get_combinacion(a, n):
    """
    Obtiene las combinaciones de pares (r, c) donde c es la combinación de n elementos tomados de a en a.
    
    Parameters:
    a (int): Número total de elementos.
    n (int): Número de elementos a tomar en cada combinación.
    
    Returns:
    list: Lista de pares (r, c).
    """
    pairs = []
    r = 2
    c = comb(n, r)
    #print(f"\tLa combinacion entre {n} y {r} es: {c}")
    if c == a:
        #print(f"\tComo la combinacion c={c} es igual que subred={a}, lo añado a la lista parejas")
        pairs.append((n, r))
    if n > 1:
        #print(f"\tComo categorias:{n} es > que 1, hago una llamada recursiva con {a} y {n-1}")
        pairs += get_combinacion(a, n - 1)
    
    return pairs

def get_categorias(subredes, categorias):
    """
    Obtiene el número máximo de subredes y las categorías correspondientes.

    Parameters:
    subredes (int): Número de subredes.
    categorias (int): Número de categorías.

    Returns:
    tuple: Número deseado de subredes y categorías correspondientes.
    """
    results = {}
    for subred in range(subredes,1,-1):
        #print(f"Para la subred {subred}, calculamos la combinacion entre {subred}y{categorias}")
        pairs = get_combinacion(subred,categorias)
        #print(f"get_combinacion me devuelve las lista de parejas {pairs}")
        for i in pairs:
            #results.append(i)
            #print(f"En el diccionario de resultados pongo la pareja {i} en la clave subred={subred}")
            results[subred]=i
    #devuelvo el numero deseado si es posible, o uno menor, para que quede una maquina libre
    if subredes in results:
        #print(f"Como en el diccionario de resultados esta el numero de subredes {subreds} lo devuelvo")
        n_subredes = subredes
    else:
        #print(f"El numero de subredes sera el maximo valor del diccionarios {results}")
        n_subredes = max(results.keys())
    #print(f"Devuelvo n_subredes={n_subredes} y results[n_subredes]={results[n_subredes]}")
    return n_subredes,results[n_subredes]

def process_skynnet_code(code, skynnet_config, fout, num_subredes, block_number):
    '''En esta funcion se aplican las transformaciones sobre el arbol de sintaxis de python
    que se han definido en las correspondientes clases
    1- Se reducen las variables de skynnet. Antes se calculan subredes y divison de datos
    2- Se almacenan las asignaciones en las que se crean los modelos
    3- Se almacenan las invocaciones que se aplican a los modelos
    4- Se indica el diccionario con la info recabada en los pasos 2 y 3
    5- Se crean las etiquetas de cloudbook necesarias para escribir la funcion skynnet
    Extra: Se añade el model number, porque puede haber varios modelos en un script'''

    #Para tratar el codigo con ast se parsea primero
    ast_code = ast.parse(code)

    #Paso 0-Se separa el post-codigo despues del predict, es decir, el uso de la red
    '''linea_predict = encontrar_linea_predict(ast_code)
    if linea_predict!=-1:
        ast_code,post_predict_code = dividir_arbol_en_dos(ast_code,linea_predict)
    else:
        post_predict_code = None 
    print(linea_predict)
    '''

    #Paso 1 - Se consultan las categorias mirando la ultima capa de tipo _NEURON_
    reduccion = num_subredes # capas=capas/reduccion  datos= datos/reduccion
    visit_categorias = VisitLastNeuron()
    visit_categorias.visit(ast_code)
    last_neuron = visit_categorias.last_neuron
    if last_neuron == ('NEURON_X',0):
        print("Warning there is no _NEURON_ variable at last layer, using generic variable it will no conflict with code")
    #print(last_neuron)
    if skynnet_config['Type'] == 'MULTICLASS':
        categorias = visit_categorias.n_categorias #Esto es igual que last_neuron[1]
        print(f"Son {categorias} categorias originales")
        #Se calcula cuantas subredes quedaran
        #num_subredes,combinatorio = get_categorias(num_subredes, categorias)
        try:
            num_subredes,combinatorio = get_categorias(num_subredes, categorias)
        except Exception as e:
            print(f"Error en el calculo de categorias, prueba un numero de subredes mas grande")
            sys.exit()
        grupos = combinatorio[0]
        tomados = combinatorio[1]
        print(f"Para formar subredes=C{combinatorio} es decir {grupos} categorias tomados de {tomados} en {tomados}")
        print(f"numero de grupos es {grupos}")
        print(f"El numero de subredes va a ser {num_subredes}")
        categorias_subred = ((categorias/grupos)*tomados)
        print(f"Categorias por subred: {categorias_subred}")
        reduccion = (categorias/categorias_subred)
        print(f"la reduccion sera por {reduccion} esto es por defecto")
    elif skynnet_config['Type'] == 'BINARYCLASS':
        reduccion = 2
        last_neuron = (last_neuron[0],2)
        num_subredes = 2
        grupos = 2
        categorias = 2
    elif skynnet_config['Type'] == 'REGRESSION':
        categorias = last_neuron[1]
        grupos = num_subredes
        reduccion = num_subredes
    
    #Paso 2 - Reduccion de datos, se reducen las variables de datos indicadas
    reduction_permission = VisitAssignSkVars(reduccion)
    reduction_permission.visit(ast_code)
    node_data_vars_reduced = TransformAssignSkVars(reduccion).visit(ast_code)
    
    #Paso 3 - Se guardan en un diccionario los modelos y sus funciones
    model_functions = VisitModelFunctions()
    model_functions.visit(node_data_vars_reduced)
    sk_dict = model_functions.dict_modelo
    #print(f"Paso 3 ======> {sk_dict}")
    #sk_dict contiene todos los nodos de las funciones que busco
    
    #Paso 4 - Se guarda en el diccionario de modelos, los datos de cada modelo
    #Una vez tengo el skdict, puedo guardar los datos de entrenamiento, test y validacion
    hay_prediccion = False #Variable para hacer la funcion predict o no, si no la hay poner un pass en la funcion
    hay_prediccion = 'predict' in sk_dict
    GetModelDataVars(sk_dict).visit(node_data_vars_reduced)
    #Ahora se busca el model.input, para saber en que punto insertar la division de datos, antes de que los metas en la red
    getInputModel(sk_dict).visit(node_data_vars_reduced) #aqui cojo el nodo antes de crear la red, para meter la division de datos y la ultima neurona antes
    if "input" not in sk_dict:
        sk_dict["input"] = sk_dict["creation"] #Si no usas el modelo funcional TODO: Eliminar en el futuro
    #print(sk_dict)
    #print(f"Paso 4 ======> {sk_dict}")
    
    #Paso intermedio, modifico los model_load y los save
    ModifyPaths(sk_dict).visit(node_data_vars_reduced)


    #Paso 5 - Quito la prediccion del nodo de codigo que tengo hasta ahora
    #Quito la prediccion y la guardo para meterla en una funcion nueva solo de la forma predicted = model.predict()
    predictions =  RemovePredictionNode(sk_dict)
    node_data_vars_reduced = predictions.visit(node_data_vars_reduced)
    #Paso 5.5 - Divido el arbol en dos a partir de la linea TODO: Debe funcionar bien si estan vacios
    prediction_nombre = predictions.predict_nombre
    nodos_post_predict = predictions.lista_nodos_post_predict
    
    #Paso 6 - Variables globales predictions_bloque_modelo={}
    #Cada predictions es un diccionario con la prediccion de cada subred
    #Escribo las variables globales, una por modelo que haya en el bloque
    #number_of_models = len(sk_dict)
    global_predictions_declarations = []
    global_cloudbook_label = Expr(value=Comment(value='#__CLOUDBOOK:GLOBAL__'))
    global_predictions_declarations.append(global_cloudbook_label)
   
    global_pred_assignment = Assign(targets=[ast.Name(id=f"predictions_{block_number}", ctx=ast.Store())],  # El objetivo de la asignación es el nombre "predictions"
                            value=ast.Dict(keys=[], values=[]),  # El valor asignado es un diccionario vacío {}
                            )
    global_pred_expr = Expr(value=global_pred_assignment)
    global_predictions_declarations.append(global_pred_expr)
    fixed_predictions = map(lambda x: unparse(fix_missing_locations(x)), global_predictions_declarations)
    fout.writelines(fixed_predictions)
    #TODO Ver si merece la pena llamarlo como el nombre del modelo en lugar de un indice, por si hay varios ficheros con bloques SKYNNET
    
    #Paso 7 - Variables nonshared modelo=[] y precision_compuesta=[]. El modelo permite una lista de modelos que cada vez se invoca con un indice
    #en caso de que una maquina ejecute secuencialmente varios submodelos.
    nonshared_models_declarations = []
    nonshared_cloudbook_label = Expr(value = Comment(value='#__CLOUDBOOK:NONSHARED__'))
    nonshared_models_declarations.append(nonshared_cloudbook_label)
   
    model_name = sk_dict['name']
    nombre = ast.Name(id=model_name, ctx=ast.Store())
    #valor = ast.NameConstant(value=None) #Esto era cuando no teniamos array de modelos
    ##valor = ast.List(elts=[], ctx=ast.Load())
    params_lista = [ast.Name(id='None', ctx=ast.Load()) for i in range(num_subredes)]
    valor = ast.List(elts=params_lista, ctx=ast.Load())
    model_name_declaration = ast.Assign(targets=[nombre], value=valor)
    model_name_expression = ast.Expr(value = model_name_declaration) #Como expresion para que separe las asignaciones en lineas distintas
    nonshared_models_declarations.append(model_name_expression)

    #Incluyo la variable nonlocal predicted_models para que los agentes sepan que predecir y no predigan un modelo que no tienen
    nonshared_predicted_models = parse("to_predict_models = []")
    nonshared_predicted_models_expr = Expr(value = nonshared_predicted_models)
    nonshared_models_declarations.append(nonshared_predicted_models_expr)

    fixed_nonshared = map(lambda x: unparse(fix_missing_locations(x)), nonshared_models_declarations)
    fout.writelines(fixed_nonshared)
    #Añado la precision compuesta como una variable nonshared ##No hace falta, la declaro localmente al predecir
    #precision_compuesta= parse("precision_compuesta=[]")
    #fout.write(unparse(fix_missing_locations(Expr(value = precision_compuesta))))
    
    #Paso 8: Funcion skynnet block que divide datos, crea y entrena modelos
    #Se llama block por el bloque skynnet que gestiona, puede trabajar con varios modelos
    for i in sk_dict['data_test']:
        print(i)
        remover = NodeRemover(i)
        node_data_vars_reduced = remover.visit(node_data_vars_reduced)
    parallel_cloudbook_label = Expr(value=Comment(value='#__CLOUDBOOK:PARALLEL__'))
    fout.write(unparse(fix_missing_locations(parallel_cloudbook_label)))
    #Aqui cambiamos los model por model[i]
 
    ModelArrayTransform(model_name).visit(node_data_vars_reduced)
    func_node = FunctionDef(
        name="skynnet_train_" + str(block_number),
        args=arguments(args=[ast.arg(arg='sk_i', annotation=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[], posonlyargs=[]),
        body=[node_data_vars_reduced],
        decorator_list=[])
  
    global_node = Global(names=[model_name])
    func_node.body.insert(0,global_node)
    #Tambien se añade como global el to_predict_models
    global_node = Global(names=["to_predict_models"])
    func_node.body.insert(1,global_node)
    #por ultimo meto el append(sk_i)
    update_trained_subnet = parse("to_predict_models.append(sk_i)")
    #update_trained_subnet = Expr(value=update_trained_subnet)
    func_node.body.append(update_trained_subnet)


    fout.write("\n")#Para evitar que el func_node se escriba en la misma linea que el comentario
    #Meto antes del nodo de creacion del modelo, el codigo para calcular la division de los datos
    composed_measure = "" #Esta variable solo interesa en el predict, es para ver si calculo accuracy o loss o ambos
    if skynnet_config['Type'] == 'MULTICLASS':
        inserta_filtro_datos(func_node,"general",sk_dict,categorias,grupos,last_neuron,'MULTICLASS', composed_measure, prediction_nombre)
    elif skynnet_config['Type'] == 'BINARYCLASS':
        inserta_filtro_datos(func_node,"general",sk_dict,categorias,grupos,last_neuron,'BINARYCLASS', composed_measure, prediction_nombre)
    elif skynnet_config['Type'] == 'REGRESSION':
        inserta_filtro_datos(func_node,"general",sk_dict,categorias,grupos,last_neuron,'REGRESSION', composed_measure, prediction_nombre)
    
    #Antes de escribir la funcion busco si tiene funciones internas y escribo el nonlocal de las variables necesarias
    nonlocal_adder = NonlocalAdder(sk_dict,'train')
    func_node = nonlocal_adder.visit(func_node)

    fout.write(unparse(fix_missing_locations(func_node)))
    
    #Paso 9 - Se escribe la funcion de la prediccion skynnet_prediction_block
    #preparo el predict_data por si no hay prediccion
    predict_data = None
    #En principio se refiere a un bloque skynnet con n modelos
    if hay_prediccion: #si no la hay escribo la funcion con un pass
        fout.write(unparse(fix_missing_locations(parallel_cloudbook_label)))
        #Declara como variables globales el diccionario de prediccion compuesta y la lista de modelos ya que los va a usar
        prediction_vars = []
        prediction_vars.append(f"predictions_{block_number}")
        global_predictions_vars = []
        for prediction in prediction_vars:
            global_predictions_vars.append(Global(names=[prediction]))
        #Despues del las predicciones meto el predicted models, que es necesario para que cada agente sepa a quien ha entrenado
        predicted_models_vars = (Global(names=["to_predict_models"]))
        global_predictions_vars.append(predicted_models_vars)
        model_vars = []
        #for model_name in sk_dict.keys():
        #    model_vars.append(Global(names=[model_name]))
        model_vars.append(Global(names=[model_name]))
        #beginremove endremove: para que funcione la prediccion compuesta fuera de cloudbook
        beginremove_cloudbook_label=Comment(value='#__CLOUDBOOK:BEGINREMOVE__')
        cloudbook_var_prepare = ast.parse("__CLOUDBOOK__ = {}\n__CLOUDBOOK__['agent'] = {}")
        cloudbook_var = Subscript(
            value=Subscript(
                value=Name(id="__CLOUDBOOK__", ctx=Load()),
                slice=Index(value=Str(s="agent")),
                ctx=Load()
            ),
            slice=Index(value=Str(s="id")),
            ctx=Store()
        )
        value = Str(s="agente_skynnet")
        cloudbook_var_assig = Assign(targets=[cloudbook_var], value=value)
        endremove_cloudbook_label=Comment(value='#__CLOUDBOOK:ENDREMOVE__')
        #Preparo las labels
        #El diccionario de predicciones contiene labels, que son para identificar que maquina se encarga de que subred
        label_var = Name(id="label",ctx=Load())
        #Para permitir varios modelos por agente tengo que añadir str(sk_i) al label
        value=ast.BinOp(
            left=cloudbook_var,     # Variable adios
            op=ast.Add(),                                  # Operador de suma
            right=ast.BinOp(
                left = Str(s='_'),
                op=ast.Add(),
                right=ast.Call(
                    func=ast.Name(id='str', ctx=ast.Load()),    # Función str
                    args=[ast.Name(id='sk_i', ctx=ast.Load())],    # Argumento i
                    keywords=[]
                )
            )
        )
        assignation_cb_dict = Assign(targets=[label_var], value=value)
        #Asignacion de predicciones, es el final de la funcion, el predictions_x_y[label] = resul
        predictions_assignements = []
        nombre = prediction_vars[0]
        valor = Name(id="resul", ctx=ast.Load())
        prediction_var_target = Subscript(
            value=Name(id=nombre,ctx=Load()),
            slice=Index(value=label_var)
            )
        prediction_assignment = Assign(targets=[prediction_var_target], value=valor)
        fix_missing_locations(prediction_assignment)
        #print(unparse(prediction_assignment))
        predictions_assignements.append(prediction_assignment)

        #Para ejecutar todos los modelos que le toquen al agente se hace un bucle sobre os modelos que les toca
        #bucle for
        to_pred_for_loop = For(
            target=Name(id='sk_i', ctx=Store()),
            iter= Subscript(
                value= Name(id='to_predict_models', ctx= Load()),
                slice= Slice(lower=None, upper=None, step=None),
                ctx= Load()
                ),
            body=[assignation_cb_dict, predictions_assignements],
            orelse=[]
        )
        
        #crear la funcion y meterle lo anterior en el body
        pred_func_node = FunctionDef(
            name="skynnet_prediction_" + str(block_number),
            #args=arguments(args=[ast.arg(arg='sk_i', annotation=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[], posonlyargs=[]),
            args=arguments(args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[], posonlyargs=[]),
            #body=[global_predictions_vars,model_vars,beginremove_cloudbook_label,cloudbook_var_prepare,cloudbook_var_assig, endremove_cloudbook_label,assignation_cb_dict, predictions_assignements],
            body=[global_predictions_vars,model_vars,beginremove_cloudbook_label,cloudbook_var_prepare,cloudbook_var_assig, endremove_cloudbook_label],
            decorator_list=[]
        )
        fout.write("\n")
        #insertar el data_test
        #print(skynnet_config['Options'])
        measure_options = skynnet_config['Options']        
        if "ACC" in measure_options and "LOSS" in measure_options:
            composed_measure = "acc,loss"
        if "ACC" in measure_options and "LOSS" not in measure_options:
            composed_measure = "acc"
        if "ACC" not in measure_options and "LOSS" in measure_options:
            composed_measure = "loss"
        if "ACC" not in measure_options and "LOSS" not in measure_options:
            composed_measure = ""
        #print(composed_measure)
        predict_data = None
        
        to_insert_nodes = sk_dict['data_test']
        predict_data = to_insert_nodes
        pred_func_node.body.insert(2,to_insert_nodes)
        '''if skynnet_config['Type'] == 'MULTICLASS':
            inserta_filtro_datos(pred_func_node,"predict",sk_dict,categorias,grupos,last_neuron,'MULTICLASS', composed_measure, prediction_nombre)
        elif skynnet_config['Type'] == 'BINARYCLASS':
            inserta_filtro_datos(pred_func_node,"predict",sk_dict,categorias,grupos,last_neuron,'BINARYCLASS', composed_measure, prediction_nombre)
        elif skynnet_config['Type'] == 'REGRESSION':
            inserta_filtro_datos(pred_func_node,"predict",sk_dict,categorias,grupos,last_neuron,'REGRESSION', composed_measure, prediction_nombre)
        '''
        #Cambios por uso del bucle de to_predict_models
        to_insert_node = preparacion_datos_predict("test",categorias,grupos,last_neuron,skynnet_config['Type'],model_name, composed_measure, prediction_nombre)
        to_pred_for_loop.body.insert(1,to_insert_node) #En el predict es distinto, se exactamente donde insertar
        remove_model = parse("to_predict_models.remove(sk_i)")
        to_pred_for_loop.body.insert(0,remove_model)

        #locks de cloudbook para no repetir ejecuciones
        lock_cloudbook_label=Comment(value='#__CLOUDBOOK:LOCK__')
        unlock_cloudbook_label=Comment(value='#__CLOUDBOOK:UNLOCK__')

        pred_func_node.body.append(lock_cloudbook_label)
        pred_func_node.body.append(to_pred_for_loop)
        pred_func_node.body.append(unlock_cloudbook_label)


        fout.write(unparse(fix_missing_locations(pred_func_node)))

    else:
        #print(block_number)
        fout.write(sk_extra_codes.pred_func_por_defecto(block_number))

    fout.write('\n\n')
    for i in sk_dict:
        print(f"    {i}:{sk_dict[i]}")

    return num_subredes,prediction_nombre,nodos_post_predict,predict_data

def write_sk_block_invocation_code(block_number,fo, skynnet_config, nombre_predict, nodos_post_predict, predict_data):
    '''Escribe la funcion con el bucle, va en la du_0
    #DU_0
    def skynnet_train_global_n():
      for i in subredes:
        assign_unique_id(i) #y filtrar datos 
        #en la herramienta no hace nada
      for i in subredes:
        skynnet()
        #cloudbook:sync
    '''
    #=====================================
    measure_options = skynnet_config['Options']        
    if "ACC" in measure_options and "LOSS" in measure_options:
        composed_measure = "acc,loss"
    if "ACC" in measure_options and "LOSS" not in measure_options:
        composed_measure = "acc"
    if "ACC" not in measure_options and "LOSS" in measure_options:
        composed_measure = "loss"
    if "ACC" not in measure_options and "LOSS" not in measure_options:
        composed_measure = ""
    #=====================================
    nodos_ast = []
    #creo nodo de comentario, y de funcion, y con el cuerpo, como es por defecto, lo puedo hacer con texto y parsearlo. y hacerle un fix missing locations o algo asi
    comment_du0 = Comment(value = "#__CLOUDBOOK:DU0__")
    fo.write(unparse(fix_missing_locations(comment_du0)))
    fo.write("\n")
    #hago el parametro subredes del bucle for
    range_call = Call(
        func=Name(id='range', ctx=Load()),
        args=[Num(num_subredes)],
        keywords=[],
    )
    #llamada a funcion skynnet_train_n
    skynnet_call = Expr(
        value=Call(
            func=Name(id='skynnet_train_'+str(block_number), ctx=Load()),
            args=[ast.arg(arg='i', annotation=None)],
            keywords=[],
        )
    )
    #bucle for
    for_loop = For(
        target=Name(id='i', ctx=Store()),
        iter=range_call,
        body=[skynnet_call],
        orelse=[],
    )
    #comentario sync
    comment_sync = Comment(value = "#__CLOUDBOOK:SYNC__")
    #funcion
    func_def = FunctionDef(
        name=f'skynnet_train_global_{block_number}',
        args=arguments(args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[], posonlyargs=[]),
        body=[for_loop,comment_sync],
        decorator_list=[],
        returns=None,
    )
    fo.write(unparse(fix_missing_locations(func_def)))
    fo.write("\n")
    #=====================================================
    fo.write(unparse(fix_missing_locations(comment_du0)))
    fo.write("\n")
    skynnet_pred_call = Expr(
        value=Call(
            func=Name(id='skynnet_prediction_'+str(block_number), ctx=Load()),
            #args=[ast.arg(arg='i', annotation=None)],
            args=[],
            keywords=[],
        )
    )
    #bucle for
    for_pred_loop = For(
        target=Name(id='i', ctx=Store()),
        iter=range_call,
        body=[skynnet_pred_call],
        orelse=[],
    )
    #Prediccion y loss compuesta
    codigo_medidas_extra = sk_extra_codes.codigo_medidas_extra(skynnet_config,composed_measure,block_number,nombre_predict)
    codigo_medidas_extra = fix_missing_locations(parse(codigo_medidas_extra))
    #funcion
    func_pred_def = FunctionDef(
        name=f'skynnet_prediction_global_{block_number}',
        args=arguments(args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[], posonlyargs=[]),
        body=[for_pred_loop,comment_sync,codigo_medidas_extra,nodos_post_predict],
        decorator_list=[],
        returns=None,
    )
    if predict_data != None:
        func_pred_def.body.insert(0,predict_data)
    fo.write(unparse(fix_missing_locations(func_pred_def)))
    fo.write("\n")

def write_sk_global_code(number_of_sk_functions,fo):
    '''escribo un if name al final del fichero que invoca a las funciones de cada modelo necesarias, solo invocaciones, las definciones en 
    la funcion sk_model_code. Esta invocacion debería ir en la du_0
    if name = main:
        skynnet_train_global_0()
        skynnet_train_global_n()
        predicted_1 = bla bla'''
    
    # Creamos una lista de nombres de función con el patrón "skynnet_train_global_{i}"
    func_names = [f"skynnet_train_global_{i}" for i in range(number_of_sk_functions)]
    func_pred_names = [f"skynnet_prediction_global_{i}" for i in range(number_of_sk_functions)]
    # Creamos una lista de llamadas a función con los nombres generados y los índices del 0 a n
    func_calls = [Call(func=Name(id=name, ctx=ast.Load()), args=[], keywords=[]) for name in func_names]
    func_pred_calls = [Call(func=Name(id=name, ctx=ast.Load()), args=[], keywords=[]) for name in func_pred_names]

    #Permito un main especial del usuario en un bloque try,except
    opt_main = fix_missing_locations(parse(sk_extra_codes.optional_main))
    
    #Hacemos una funcion cloudbook main, primero la etiqueta y luego la funcion
    comment_main = Comment(value = "#__CLOUDBOOK:MAIN__")
    fo.write(unparse(fix_missing_locations(comment_main)))
    fo.write("\n")
    #funcion
    main_def = FunctionDef(
        name="sk_main",
        args=arguments(args=[], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[], posonlyargs=[]),
        body=[opt_main],#Expr(value=call) for call in func_calls],
        decorator_list=[],
        returns=None,
    )
    for call in range(number_of_sk_functions):
        main_def.body.append(Expr(value=func_calls[call]))
        main_def.body.append(Expr(value=func_pred_calls[call]))
    fix_missing_locations(main_def)
    fo.write(unparse(main_def))
    fo.write('\n\n')


    # Creamos un bloque if __name__ == "__main__" que contiene todas las llamadas a función generadas
    # Creamos una llamada a la función main()
    main_call = Call(func=Name(id="sk_main", ctx=Load()), args=[], keywords=[])
    main_block = If(
        test=Compare(left=Name("__name__", Load()), ops=[Eq()], comparators=[Str("__main__")]),
        body=[Expr(value=main_call)],
        orelse=[]
    )
    fix_missing_locations(main_block)
    fo.write(unparse(main_block))

def main_skynnet(carpeta,file,n_subredes):
    global num_subredes
    n = n_subredes
    orig_file = carpeta+"//"+file
    print(orig_file)
    print(f"num subredes original {n_subredes}")
    #sk_file = create_new_file(file)#Done cambiar para que lo cree en la misma ubicacion
    sk_file = ""
    if file.find(".py") == -1:
        sk_file = carpeta+"//"+"sk_"+file+".py"
    else:
        sk_file = carpeta+"//"+"sk_"+file
    open(sk_file, "w").close() #python deberia cerrarlo automaticamente, pero queda mas claro asi
    sk_trees,init_code,post_sk_codes,skynnet_configs = prepare_sk_file(orig_file)
    print(skynnet_configs)
    num_sk_blocks = len(skynnet_configs) #Cuantos bloques skynnet hay
    with open(sk_file,'w') as fo:
        #escribo el principio
        fo.write(init_code)
        fo.write(sk_extra_codes.funciones_combinatorias)
        for block_number in range(num_sk_blocks):
            code = sk_trees[block_number]
            num_subredes,prediction_nombre,nodos_post_predict,predict_data = process_skynnet_code(code, skynnet_configs[block_number], fo, n, block_number)
            #escribo el final
            fo.write(post_sk_codes[block_number])
            fo.write("\n\n")
            #Escribo la llamada a los modelos del bloque
            write_sk_block_invocation_code(block_number,fo,skynnet_configs[block_number],prediction_nombre,nodos_post_predict,predict_data)
        fo.write("\n\n")
        #Escribo la llamada a todos los bloques
        write_sk_global_code(num_sk_blocks,fo)
        fo.write("\n\n")
    ##Cambiamos indentacion de espacios a tabuladores para cloudbook
    tab_indent(sk_file)
    #Se borra el fichero original y dejar el sk_xxx
    os.remove(orig_file)

def main(test=False):
    '''Procesa el fichero de entrada y genera el de salida'''
    global num_subredes
    global file
    print(file)
    print(f"num subredes original {num_subredes}")
    sk_file = create_new_file(file)
    #Si es test el fichero se coge de otro lado
    if test:
        file = "test/"+file
    else:
        file = "input/"+file
    sk_trees,init_code,post_sk_codes,skynnet_configs = prepare_sk_file(file)
    print(skynnet_configs)
    num_sk_blocks = len(skynnet_configs) #Cuantos bloques skynnet hay
    with open(sk_file,'w') as fo:
        #escribo el principio
        fo.write(init_code)
        fo.write(sk_extra_codes.funciones_combinatorias)
        for block_number in range(num_sk_blocks):
            code = sk_trees[block_number]
            num_subredes,prediction_nombre,nodos_post_predict,predict_data = process_skynnet_code(code, skynnet_configs[block_number], fo, n, block_number)
            #escribo el final
            fo.write(post_sk_codes[block_number])
            fo.write("\n\n")
            #Escribo la llamada a los modelos del bloque
            write_sk_block_invocation_code(block_number,fo,skynnet_configs[block_number],prediction_nombre,nodos_post_predict,predict_data)
        fo.write("\n\n")
        #Escribo la llamada a todos los bloques
        write_sk_global_code(num_sk_blocks,fo)
        fo.write("\n\n")
    ##Cambiamos indentacion de espacios a tabuladores para cloudbook
    tab_indent(sk_file)

if __name__=="__main__":
    if len(sys.argv) == 3:
        n = int(sys.argv[2])
        file = sys.argv[1]
        if file.find(".py") == -1:
            file = file+".py"
        print("Fichero: {} en {} subredes".format(file,n))
        num_subredes = n
        main()
    elif len(sys.argv) == 2:
        if sys.argv[1]=='test':
            n = 4
            num_subredes = n
            test = True
            carpeta = "./test"
            for test_file in glob.glob(carpeta+'/*'):
                file = test_file.replace(carpeta,"")[1:]
                #print(file)
                main(test)
        else:
            print("Usage: py sk_tool.py file num_machines")
            sys.exit()
    else:
        print("Usage: py sk_tool.py file num_machines")
        sys.exit()
    '''
    if len(sys.argv)!=3:
        print("Usage: py sk_tool.py file num_machines")
        sys.exit()
    elif len(sys.argv) == 2:
        if sys.argv[1]=='test':
            n = 4
            test = True
            carpeta = "./test"
            for test_file in glob.glob(carpeta+'/*'):
                file = test_file
                main(test)
            import subprocess
            # Ruta al archivo batch que deseas ejecutar
            ruta_archivo_bat = './output/test_all.bat'
            # Ejecuta el archivo batch
            #subprocess.call([ruta_archivo_bat])
        else:
            print("Usage: py sk_tool.py file num_machines")
            sys.exit()
    else:
        n = int(sys.argv[2])
        file = sys.argv[1]
        if file.find(".py") == -1:
            file = file+".py"
        print("Fichero: {} en {} subredes".format(file,n))
        num_subredes = n
        main()'''


