import re
import pyodbc
#conn = pyodbc.connect('Driver={SQL Server};'
#                      'Server=AKSHAY-KUMAR;'
#                      'Database=P4;'
#                      'Trusted_Connection=yes;')

conn = pyodbc.connect('Driver={SQL Server};'
                      'Server=DESKTOP-FCAMJHE\SQLEXPRESS;'
                      'Database=test_fifa;'
                      'Trusted_Connection=yes;')

cursor = conn.cursor()
cursor.execute('select attribute_name,dataType from dbo.category_attributes union select attribute,dataType from dbo.infoAttribute;')

dictType = dict()

for row in cursor:
    dtype=str()
    if row[1]=='float':
        dtype='float(4)'
    elif row[1]=='boolean':
        dtype='bit'
    else:
        dtype=row[1]
    dictType[row[0].replace(' ','_')]= dtype


cursor.execute('SELECT * FROM dbo.p_info')

data_objects=[]
dtype=[]

for row in cursor:
    data_objects.append(row[0])


fact_attributes_dict={}
facts=[]
dimensions=[]
dimensions_attributes_dict={}
foreign_key_list=set()

time_dim_table=[]

for data_object in data_objects:
    #line 2
    facts.append(data_object)
    fact_attributes_dict.setdefault(data_object,[])
    dimensions_attributes_dict.setdefault(data_object, {})
    dimensions = []
    sub_dimension_dict = {}

    #line 3-5 Read and store facts
    cursor.execute("select* from dbo.infoAttribute where p_info like '%{}%'".format(data_object))
    for row in cursor:
        fact_attributes_dict[data_object].append(row[1])

    # fetch all dataobjects that contain other data objects
    cursor.execute("select * from dbo.infoAttribute where p_info like '%{}%' and dataType like '%data object%'".format(data_object))
    data_dim = []
    for row in cursor:
        data_dim.append(row[1])
    data_dim = list(set(data_dim))


    #Line 6-12 handling data objects within data objects
    if len(data_dim) != 0:
        for d in data_dim:
            temp_dict={}
            cursor.execute("select* from dbo.infoAttribute where p_info like '%{}%'".format(d))
            attributes = []
            for row in cursor:
                attributes.append(row[1])
            #print(d,attributes)
            temp_dict[d]=["{}_id".format(d)]+attributes
            dimensions.append(d)
            dimensions_attributes_dict[data_object].update(temp_dict)
            #Line 11
            foreign_key_list.add("{}_id".format(d))

    #Line13-14 Fetch category attributes
    cursor.execute("select* from dbo.category_attributes where p_info like '%{}%'".format(data_object))
    categories = []
    for row in cursor:
        categories.append(row[1])
    categories=list(set(categories))
    temp_dict={}
    for category in list(set(categories)):
        #Fetch subcategory objects
        cursor.execute("select* from dbo.category_subcategory where subcategory_of like '%{}%' and p_info like '%{}%'".format(category,data_object))
        subcategory = []
        for row in cursor:
            subcategory.append(row[1])

        #Line 15-24 Adding category object as dimension and handling its attributes
        if category not in dimensions:
            dimensions.append(category)
            cursor.execute("select* from dbo.category_attributes where p_info like '%{}%' and category_name like '%{}%';".format(data_object,category))
            #fact_attributes_dict[data_object].append('{}_{}'.format(data_object, category))
            if category not in ["day","date","datetime"] and "date" not in category:
                temp_dict.setdefault(category,[])
                attributes=[]
                for row in cursor:
                    if "id" not in row[2]:
                        attributes.append(row[2])
                temp_dict[category]=['{}_id'.format(category)]+list(set(attributes))
                foreign_key_list.add('{}_id'.format(category))
            else:
                #foreign_key = '{}_{}'.format(data_object, category)
                #foreign_key_list.add(foreign_key)
                #time_dim_table.append(foreign_key)
                #temp_dict["Time_Dimension"]=foreign_key
                if category not in list(temp_dict):
                    foreign_key_list.add("time_id")
                    temp_dict["time_id"]="time_id"
            cursor.execute("select* from dbo.category_changeType where p_info like '%{}%' and category_name like '%{}%'".format(data_object,category));
            for row in cursor:
                if row[2]=="no_update" and row[4]=="NULL":
                    temp_dict["Timestamp"]=["TimeStamp"]
            #else:
            #    dimensions.clear()
            #
            dimensions_attributes_dict[data_object].update(temp_dict)

        #Line 25 Adding subcategory object to dimension and handling its attributes
        if len(subcategory) != 0:
            for sub_cat in set(subcategory):
                #Line 27
                if sub_cat not in list(sub_dimension_dict):
                    temp_dict={}
                    cursor.execute("select* from dbo.category_attributes where p_info like '%{}%' and category_name like '%{}%';".format(data_object, sub_cat))
                    if sub_cat not in ["day", "date"] and "date" not in sub_cat:
                        attributes = []
                        for row in cursor:
                            if "id" not in row[2]:
                                attributes.append(row[2])
                        temp_dict[sub_cat] = ['{}_id'.format(sub_cat)] + list(set(attributes))
                        foreign_key_list.add('{}_id'.format(sub_cat))
                    else:
                        if sub_cat not in list(sub_dimension_dict):
                            foreign_key_list.add("time_id")
                            temp_dict["time"] = "time_id"
                    #print(temp_dict)
                    #Line 31-33
                    cursor.execute("select* from dbo.category_changeType where p_info like '%{}%' and category_name like '%{}%'".format(data_object, category));
                    for row in cursor:
                        if row[2] == "no_update" and row[4] == "NULL":
                            temp_dict["Timestamp"] = ["TimeStamp"]
                    sub_dimension_dict.update(temp_dict)
            # line 34-36
            dimensions_attributes_dict[data_object][category].append(sub_dimension_dict)

#print("Facts are ",facts)
#print("--------------------------------")
#print(fact_attributes_dict)
#print("--------------------------------")
dimensions_list=[]
for key,dim_dict in dimensions_attributes_dict.items():
    dimensions_list.append(dim_dict)
#print(dimensions_list)
#print("--------------------------------")

f = open("output.txt", "w")


flag = 0
cursor.execute("select count(*) from p_info where history_duration is not NULL;")
for row in cursor:
    flag = row[0]

# Handling time dimension
d = ['time_id', 'date', 'day', 'week', 'month', 'quarter', 'year']
foreign_key_list.add("time_id")

if flag > 0:
    #    foreign_key_list.append('time_id')
    #    print(foreign_key_list)
    f.write("Time Dimension Table {}\n".format(d))
    print("Time Dimension Table {}".format(d))
    f.write("--------------------------------\n")
    print("--------------------------------")


fact_table_list=[]
for l in fact_attributes_dict.values():
    fact_table_list=list(set(fact_table_list+l))

foreign_key_list=list(foreign_key_list)

fact_table_list=foreign_key_list+fact_table_list


#print("Fact Table",["Date"]+list(set(fact_table_list).difference(time_dim_table)))

fact_table_list=[x.replace(' ','_') for x in fact_table_list]
f.write("Fact Table {}\n".format(fact_table_list))
print("Fact Table",fact_table_list)
f.write("--------------------------------\n")
print("--------------------------------")
#print(foreign_key_list)
#print("--------------------------------")
#flag=0
#for key in foreign_key_list:
#    if "date" in key.lower() or "day" in key.lower():
#        flag=1



dim_tables_dict={}
for category_dict in dimensions_list:
    for key,val in category_dict.items():
        if key not in list(dim_tables_dict):
            if val[0] in foreign_key_list:
                dim_tables_dict[key]=category_dict[key]#+[category_dict["Time_Dimension"]]
            #else:
            #    dim_tables_dict[key]+=[category_dict["Time_Dimension"]]
        
table_prim=dict()

#Print Dimensions
for key,val in dim_tables_dict.items():
    final_val=set()
    for x in val:
        if type(x) is dict:
            for k,v in x.items():
                for i in v:
                    if i in foreign_key_list:
                        final_val.add(i)
        else:
            if x in foreign_key_list:
                table_prim[x.replace(' ','_')]="{}_TABLE".format(key.replace(' ','_'))
            final_val.add(x)
    
    
    val=final_val
    val=[x.replace(' ','_') if type(x) is not dict else x for x in val]
    dim_tables_dict[key]=val
    print("{} Dimension Table".format(key),val)
    f.write("{} Dimension Table: {}\n".format(key,val))
    print("--------------------------------")
    f.write("--------------------------------\n")
    
#print(table_prim)
    

print("Creating schema with fact and dimension tables...\n")
f.write("Creating schema with fact and dimension tables...\n")

#print(dim_tables_dict)

#Creating fact and dimension tables in P1 database
last=[]
for key in dim_tables_dict.keys():
    c = cursor.execute("SELECT count(*) FROM INFORMATION_SCHEMA.TABLES where TABLE_NAME='{}_TABLE'".format(key.replace(' ','_')))
    counter = c.fetchone()[0]
    last_flag = 0
    if counter == 0:
        try:
            createSQL = "CREATE  TABLE DBO.{}_TABLE (".format(key.replace(' ','_'))
            flag=0
#            print(dim_tables_dict[key])
            for ele in dim_tables_dict[key]:
                flag=1
                ele=ele.replace(' ','_')
                key=key.replace(' ','_')
#                print(key,ele)
                if ele in table_prim.keys():
                    if re.match(key,ele):
                        createSQL+="{} int IDENTITY(1,1) PRIMARY KEY,".format(ele)
                    else:
                        last_flag=1
                        createSQL+="{} int REFERENCES {}({}),".format(ele,table_prim[ele],ele)
                else:
                        createSQL+="{} {},".format(ele,dictType[ele])
                
            createSQL = createSQL[:-1]
            createSQL+=");"
            
            if flag==1:
                if last_flag==1:
                    last.append(createSQL)
                else:
                    print(createSQL,'\n')
                    f.write(createSQL)
                    f.write('\n')
                    cursor.execute(createSQL)
                    cursor.commit()
        except:
            None
    else:
        print("{}_TABLE already exists".format(key.replace(' ','_')));
        f.write("{}_TABLE already exists\n".format(key.replace(' ','_')))

for createSQL in last:
    print(createSQL,'\n')
    f.write(createSQL)
    f.write('\n')
    cursor.execute(createSQL)
    cursor.commit()
   
c = cursor.execute("SELECT count(*) FROM INFORMATION_SCHEMA.TABLES where TABLE_NAME='TIME_TABLE'")
counter = c.fetchone()[0]

if counter == 0:
    try:
        createSQL = "CREATE TABLE DBO.TIME_TABLE ("
        flag=0
        for ele in d:
            flag=1
            if ele == 'date':
                createSQL+="{} date,".format(ele)
            elif ele in foreign_key_list:
                ele=ele.replace(' ','_')
                createSQL+="{} int IDENTITY(1,1) PRIMARY KEY,".format(ele)
                table_prim[ele]="TIME_TABLE"
            else:
                ele=ele.replace(' ','_')
                createSQL+="{} int,".format(ele)
            
        createSQL = createSQL[:-1]
        createSQL+=");"
        
        if flag==1:
            print(createSQL,'\n')
            f.write(createSQL)
            f.write('\n')
            cursor.execute(createSQL)
            cursor.commit()
    except:
        None
else:
    print("TIME_TABLE already exists");
    f.write("TIME_TABLE already exists\n")
    

c = cursor.execute("SELECT count(*) FROM INFORMATION_SCHEMA.TABLES where TABLE_NAME='FACT_TABLE'")
counter = c.fetchone()[0]

if counter == 0:
    try:
        createSQL = "CREATE  TABLE DBO.FACT_TABLE ("
        flag=0
        for ele in fact_table_list:
            flag=1
            ele=ele.replace(' ','_')
            if ele in table_prim:
                createSQL+="{} int REFERENCES {}({}),".format(ele,table_prim[ele],ele)
            else:
                if ele not in dictType:
                    createSQL+="{} int,".format(ele)
                elif dictType[ele]!='data object':
                    createSQL+="{} {},".format(ele,dictType[ele])
                
        createSQL = createSQL[:-1]
        createSQL+=");"
        
        if flag==1:
            print(createSQL,'\n')
            f.write(createSQL)
            f.write('\n')
            cursor.execute(createSQL)
            cursor.commit()
    except:
        None
else:
    print("FACT_TABLE already exists");
    f.write("FACT_TABLE already exists\n")

print("\nSchema created!\n")
f.write("\nSchema created!\n")

f.close()
conn.close()
