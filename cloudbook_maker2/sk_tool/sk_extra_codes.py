

funciones_combinatorias='''
#__CLOUDBOOK:LOCAL__
def dividir_array_categorias(array, n, m):
    #n = categorias iniciales
    #m = numero de arrays resultantes
    # Obtener las categorias unicas del array original
    categorias_unicas = np.unique(array)
    
    if n < m:
        raise ValueError(f"El numero de categorias original {n} debe ser mayor o igual al numero de arrays de destino {m}.")
    
    if m > len(categorias_unicas):
        raise ValueError(f"El numero de categorias unicas {len(categorias_unicas)} no es suficiente para dividirlas en los {m} arrays deseados.")
    
    # Calcular el numero de categorias en cada array de destino
    categorias_por_array = n // m    
    # Crear los m arrays de destino
    arrays_destino = []
    inicio_categoria = 0
    
    for i in range(m):
        fin_categoria = inicio_categoria + categorias_por_array
        
        if i < n % m:#
            #print(f"\t\tComo {i} < n({n}) % m({m}), hacemos fin_categoria = {fin_categoria+1}")
            fin_categoria += 1
        
        categorias_array_actual = categorias_unicas[inicio_categoria:fin_categoria]
        arrays_destino.append(categorias_array_actual)
        inicio_categoria = fin_categoria
    return arrays_destino

#__CLOUDBOOK:LOCAL__
def combinar_arrays(arrays):
    from itertools import combinations
    if len(arrays) < 2:
        raise ValueError("Se requieren al menos dos arrays para realizar la combinacion.")
    
    combinaciones = list(combinations(arrays, 2))
    
    arrays_combinados = []
    
    for combo in combinaciones:
        array_1, array_2 = combo
        
        # Concatenar los dos arrays en uno solo
        array_combinado = np.concatenate((array_1, array_2))
        
        arrays_combinados.append(array_combinado)
    
    return arrays_combinados
'''

optional_main = '''try:
    main()
except:
    pass
'''

def division_datos_gen_fit(categorias,grupos,last_neuron,tipo_red,datos_y):
    division_datos = f'''grupos_de_categorias = dividir_array_categorias({datos_y},{categorias},{grupos})
combinacion_arrays = combinar_arrays(grupos_de_categorias)[sk_i]
{datos_y} = {datos_y}[np.isin({datos_y},combinacion_arrays)]
print("======================================")
print("Skynnet Info: Categorias de esta subred",np.unique({datos_y}))
print("======================================")
categorias_incluir = np.unique({datos_y})
etiquetas_consecutivas = np.arange(len(categorias_incluir))
{last_neuron[0]} = len(combinacion_arrays)
    '''
    return division_datos

def division_datos_fit_multiclass(categorias,grupos,datos_x,datos_y,last_neuron):
    division_datos = f'''grupos_de_categorias = dividir_array_categorias({datos_y},{categorias},{grupos})
combinacion_arrays = combinar_arrays(grupos_de_categorias)[sk_i]
{datos_x} = {datos_x}[np.isin({datos_y},combinacion_arrays)]
{datos_y} = {datos_y}[np.isin({datos_y},combinacion_arrays)]
print("======================================")
print("Skynnet Info: Longitud de los datos de la subred (datos,etiquetas):",len({datos_x}),len({datos_y}))
print("Skynnet Info: Categorias de esta subred",np.unique({datos_y}))
print("======================================")
categorias_incluir = np.unique({datos_y})
etiquetas_consecutivas = np.arange(len(categorias_incluir))
{datos_y} = np.searchsorted(categorias_incluir, {datos_y})
{last_neuron[0]} = len(combinacion_arrays)
'''
    return division_datos

def division_datos_fit_binaryclass(tipo_datos,datos_x,datos_y,last_neuron):
    division_datos = f'''
datos_{tipo_datos}_x_1 = {datos_x}[:len({datos_x})//2]
datos_{tipo_datos}_x_2 = {datos_x}[len({datos_x})//2:]
datos_{tipo_datos}_y_1 = {datos_y}[:len({datos_y})//2]
datos_{tipo_datos}_y_2 = {datos_y}[len({datos_y})//2:]
if sk_i == 1:
    {datos_x} = datos_{tipo_datos}_x_1
    {datos_y} = datos_{tipo_datos}_y_1
else:
    {datos_x} = datos_{tipo_datos}_x_2
    {datos_y} = datos_{tipo_datos}_y_2
{last_neuron[0]} = 2
        '''
    return division_datos

def division_datos_fit_regression(grupos,tipo_datos,datos_y, last_neuron):
    division_datos = f'''#Is not neccesary to divide data
{tipo_datos}_splits = np.array_split({datos_y},{grupos},axis=1)
{datos_y} = {tipo_datos}_splits[sk_i]
{last_neuron[0]} = {datos_y}.shape[-1]#El tam de la ultima dimension'''
    return division_datos


def preparacion_datos_predict_multiclass(medida_compuesta,predict_name,model_name,datos_y,categorias,grupos):

    preparacion_datos = f'''grupos_de_categorias = dividir_array_categorias({datos_y},{categorias},{grupos})
categorias_incluir = combinar_arrays(grupos_de_categorias)[sk_i]
aux=f"'''+"{categorias_incluir}"+'''"
'''+f"{predict_name}"+''' = '''+f"{model_name}"+'''[sk_i].predict(_DATA_TEST_X, verbose=1)
categorias_str = aux[aux.find("[")+1:aux.find("]")]
categorias = np.fromstring(categorias_str, dtype=int,sep=' ')
resul = []
for i,pred in enumerate('''+f"{predict_name}"+'''):
    array_final = np.ones('''+f"{categorias}"+''')
    array_final[categorias] = pred
    resul.append(array_final.tolist())
'''

    return preparacion_datos

def preparacion_datos_predict_binaryclass(medida_compuesta,predict_name,categorias,model_name):

    preparacion_datos = f'''
'''+f"{predict_name}"+''' = '''+f"{model_name}"+'''[sk_i].predict(_DATA_TEST_X, verbose=1)
categorias = [0,1]
resul = '''+f"{predict_name}"+'''.tolist()
'''

    return preparacion_datos

def preparacion_datos_predict_regression(predict_name,model_name,categorias):
    preparacion_datos = f'''
'''+f"{predict_name}"+''' = '''+f"{model_name}"+'''[sk_i].predict(_DATA_TEST_X, verbose=1)
resul = '''+f"{predict_name}"+'''.tolist()
'''
    return preparacion_datos

def codigo_medidas_extra(skynnet_config,composed_measure,block_number,nombre_predict):
    '''
    codigo_prediccion_compuesta: codigo para unificar las predicciones y calcular accuracy
    prediccion_aux: codigo para unificar predicciones (necesario si solo pides loss)
    codigo_los_compuesta: codigo que calcula la loss de una prediccion
    prediccion_loss_regresion: codigo para unificar predicciones en problemas de regresion
    codigo_loss_compuesta_regresion: codigo para calcular la loss compuesta en problemas de regresion
    codigo_acc_regresion: codigo para indicar que no se calcula accuracy en problemas de regresion
    codigo_sin_predict: codigo para indicar que tienes que usar el predict en tu coigo original si quieres usar las redes
    '''
    codigo_medidas_extra = ""
    
    codigo_prediccion_compuesta =f'''global predictions_{block_number}
precision_compuesta = []
valores = np.array(list(predictions_{block_number}.values()))
{nombre_predict} = np.prod(valores,axis=0)
correctas = 0
total = 0
for i in range(len(_DATA_TEST_Y)):
    if _DATA_TEST_Y[i] == np.argmax({nombre_predict}[i]):
        correctas+=1
    total+=1
precision_compuesta.append(correctas/total)
print("============================================")
print('Skynnet Info: La accuracy de la prediccion compuesta es: ', precision_compuesta)
print("============================================")
'''
    prediccion_aux = f'''
global predictions_{block_number}
precision_compuesta = []
valores = np.array(list(predictions_{block_number}.values()))
{nombre_predict} = np.prod(valores,axis=0)
'''

    codigo_prediccion_compuesta_bin = f'''global predictions_{block_number}
precision_compuesta = []
for idx,i in enumerate(predictions_{block_number}):
        if idx == 0:
            p1=predictions_{block_number}[i]
        elif idx == 1:
            p2 = predictions_{block_number}[i]
p1 = np.array(p1)
p2 = np.array(p2)
p1 = p1.reshape((-1,2))
p2 = p2.reshape((-1,2))
{nombre_predict}=np.zeros(0)
for i in range(0, p1.shape[0]):
    a=abs(p1[i][0]-p1[i][1])
    b=abs(p2[i][0]-p2[i][1])
    
    c=a-b
        
    if c>=0:
        {nombre_predict}=np.append({nombre_predict},p1[i])
        
    else:
        {nombre_predict}=np.append({nombre_predict},p2[i])

{nombre_predict}.shape=p1.shape
correctas = 0
total = 0
for i in range(len(_DATA_TEST_Y)):
    if _DATA_TEST_Y[i] == np.argmax({nombre_predict}[i]):
        correctas += 1
    total += 1
precision_compuesta.append(correctas / total)
print('============================================')
print('Skynnet Info: La accuracy de la prediccion compuesta es: ', precision_compuesta)
print('============================================')
'''

    prediccion_aux_bin = f'''
global predictions_{block_number}
precision_compuesta = []
for idx,i in enumerate(predictions_{block_number}):
        if idx == 0:
            p1=predictions_{block_number}[i]
        elif idx == 1:
            p2 = predictions_{block_number}[i]
p1 = np.array(p1)
p2 = np.array(p2)
p1 = p1.reshape((-1,2))
p2 = p2.reshape((-1,2))
{nombre_predict}=np.zeros(0)
for i in range(0, p1.shape[0]):
    a=abs(p1[i][0]-p1[i][1])
    b=abs(p2[i][0]-p2[i][1])
    
    c=a-b
        
    if c>=0:
        {nombre_predict}=np.append({nombre_predict},p1[i])
        
    else:
        {nombre_predict}=np.append({nombre_predict},p2[i])

{nombre_predict}.shape=p1.shape
'''

    codigo_loss_compuesta = f'''
if (_DATA_TEST_Y[0].shape!=()):#La salida tiene mas de una dimension
    cce = tf.keras.losses.CategoricalCrossentropy()
    cce_orig=cce(_DATA_TEST_Y, {nombre_predict}).numpy()
    print('============================================')
    print('Skynnet Info: La loss compuesta es (cce): ', cce_orig)
    print('============================================')
else:
    scce = tf.keras.losses.SparseCategoricalCrossentropy()
    scce_orig=scce(_DATA_TEST_Y, {nombre_predict}).numpy()
    print('============================================')
    print('Skynnet Info: La loss compuesta es (scce): ', scce_orig)
    print('============================================')
'''
    prediccion_loss_regresion = f'''
global predictions_{block_number}
predictions_{block_number} = dict(sorted(predictions_{block_number}.items(), key=lambda x: int(x[0].split('_')[-1])))
{nombre_predict} = np.concatenate(list(predictions_{block_number}.values()), axis=1)
'''
    codigo_loss_compuesta_regresion = f'''
mse = tf.keras.losses.MeanSquaredError()
mse_orig=mse(_DATA_TEST_Y, {nombre_predict}).numpy()
print('============================================')
print('Skynnet Info: La loss compuesta es (mse): ', mse_orig)
print('============================================')
'''
    codigo_loss_compuesta_bin = f'''
bce = tf.keras.losses.BinaryCrossentropy()
bce_orig=bce(_DATA_TEST_Y, {nombre_predict}).numpy()
print('============================================')
print('Skynnet Info: La loss compuesta es: ', bce_orig)
print('============================================')
'''
    codigo_acc_regresion = f'''
#There is no acc calculation in regression problems
'''
    codigo_sin_predict = f'''
#Error: There is no prediction in original code, make prediction=model.predict() in order to use it
'''

    if nombre_predict != "":
        if composed_measure == "acc,loss":
            if skynnet_config['Type'] == 'MULTICLASS':
                codigo_medidas_extra = codigo_prediccion_compuesta+codigo_loss_compuesta
            elif skynnet_config['Type'] == 'BINARYCLASS':
                codigo_medidas_extra = codigo_prediccion_compuesta_bin+codigo_loss_compuesta            
            else:
                codigo_medidas_extra = codigo_acc_regresion+ prediccion_loss_regresion + codigo_loss_compuesta_regresion
        elif composed_measure == "acc":
            if skynnet_config['Type'] == 'MULTICLASS':
                codigo_medidas_extra = codigo_prediccion_compuesta
            elif skynnet_config['Type'] == 'BINARYCLASS':
                codigo_medidas_extra = codigo_prediccion_compuesta_bin
            else:
                codigo_medidas_extra = codigo_acc_regresion + prediccion_loss_regresion
        elif composed_measure == "loss":
            if skynnet_config['Type'] == 'MULTICLASS':
                codigo_medidas_extra = prediccion_aux+codigo_loss_compuesta
            elif skynnet_config['Type'] == 'BINARYCLASS':
                codigo_medidas_extra = prediccion_aux_bin+codigo_loss_compuesta
            else:
                codigo_medidas_extra = prediccion_loss_regresion+codigo_loss_compuesta_regresion
        else: #Si no pide medidas pero puede querer hacer algo con las predicciones, se unifican
            if skynnet_config['Type'] == 'MULTICLASS':
                codigo_medidas_extra = prediccion_aux
            elif skynnet_config['Type'] == 'BINARYCLASS':
                codigo_medidas_extra = prediccion_aux_bin
            else:
                codigo_medidas_extra = prediccion_loss_regresion
    else:
        codigo_medidas_extra = codigo_sin_predict

    return codigo_medidas_extra

def pred_func_por_defecto(block_number):
    codigo = f'''

#__CLOUDBOOK:PARALLEL__
def skynnet_prediction_{block_number}():
    pass
'''
    return codigo