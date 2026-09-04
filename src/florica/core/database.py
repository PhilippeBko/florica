import json
import re
import uuid

from copy import deepcopy
from datetime import datetime

from PyQt5 import  QtSql, QtWidgets, QtCore
from PyQt5.QtCore import QFile, QTextStream, Qt, QEvent, pyqtSignal

from florica.core import functions

# global functions to access to the current instance of database connexion
_registry = None
class ServiceRegistry:
    def __init__(self, dbconn, taxa=None, plot=None):
        self.db = dbconn
        self.taxa = taxa
        self.plot = plot

def init_registry(registry):
    global _registry
    if _registry is not None:
        raise RuntimeError("Registry already initialized")
    _registry = registry

def services():
    if _registry is None:
        raise RuntimeError("Registry not initialized")
    return _registry

def dbtaxa():
    return services().taxa

def dbplot():
    return services().plot
def db():
    return services().db



class DatabaseConnection (QtWidgets.QWidget):
    """
        A class for managing connections to a PostgreSQL database.
        It configures the standard methods for opening, closing, and executing connections using a `pg_connexion` dictionary containing parameters (host, username, password, database, port).
        It checks for the existence of the schema and executes the scripts necessary to create the database if required.
    """
    clicked = pyqtSignal()
    def __init__(self):
        self.db = None
        super().__init__()
        frame = QtWidgets.QFrame(self)
        frame.setStyleSheet("background-color: transparent;")
        self.setCursor(Qt.PointingHandCursor)

        self.statusIndicator = QtWidgets.QWidget(frame)
        #self.statusIndicator.setStyleSheet("background-color: rgb(255, 0, 0); border-radius: 5px;")
        self.statusIndicator.setFixedSize(10, 10)

        self.statusConnection = QtWidgets.QLabel(None, frame)
        self.statusConnection.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred)
        #self.statusConnection.setText("Not Connected")
        
        frame_layout = QtWidgets.QHBoxLayout(frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)
        frame_layout.addWidget(self.statusIndicator)
        frame_layout.addWidget(self.statusConnection)
        
        self.setLayout(frame_layout)   
    @property
    def db_dic_month (self):
        return {
            1: ["january","enero","janvier", "janv.", "jan.", "ene."], 
            2: ["february","febrero", "février", "feb.", "fev.", "fév."], 
            3: ["march", "marzo", "mars"],
            4: ["april", "abril", "avril"], 
            5: ["may", "mayo", "mai"], 
            6: ["june", "junio", "juin"],
            7: ["july", "julio", "juillet"], 
            8: ["august", "agosto", "août", "aug.", "ago."], 
            9: ["september", "septiembre", "septembre", "sept.", "sep"],
            10: ["october", "octubre", "octobre", "oct."], 
            11: ["november", "noviembre", "novembre", "nov."], 
            12: ["december", "diciembre", "décembre", "déc.", "dec.", "dic."]
        }


    def db_translate(self, value, field_def):

        _type = field_def.get("type")
        if value is None:
            value = ''
        try:
            if _type == 'integer':
                value = int(value)
            elif _type == 'numeric':
                value = float(value)
            elif _type in ['text', 'memo', 'list']:
                value = str(value).strip()
        except:
            value = ''

        if "items" not in field_def:
            return value
        
        items = field_def.get("items")

        if isinstance(value, int) and not isinstance(value, bool):
            return items[value - 1]  if 1 <= value <= len(items) else value

        if isinstance(value, str):
            #value = value.strip().lower()
            return next((x for x in items if x.lower() == value.lower()), value)
            return items.index(value) + 1 if value in items else value

        return value

    def create_template(self, dict_fieldefs):
        template = {}

        for key, value in dict_fieldefs.items():
            if isinstance(value, dict):
                if "type" in value:
                    template[key] = None
                else:
                    template[key] = self.create_template(value)
            else:
                template[key] = None

        return template
    def enterEvent(self, event):
        """Set the text in blue when mouse is over the widget."""
        self.statusConnection.setStyleSheet("color: blue;")
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Set the text normal style when mouse leaves the widget."""
        self.statusConnection.setStyleSheet("")
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Emit the clicked signal when the left mouse button is pressed."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def open(self, pg_connexion):
        """DBASE: Open a connection to a PostgreSQL database using a pg_connexion dictionary"""
        #pg_connexion = {"host": host, "user": user, "password": password, "database": database, "port": port}
        if self.db:
            if self.db.isValid():
                self.db.close()
                del self.db
            self.db = None
        self._load_status()
        port = int(pg_connexion.get("port", 5432))
        conn_name = "x-nomen" +str(uuid.uuid4())
        self.db = QtSql.QSqlDatabase.addDatabase("QPSQL", conn_name)
        self.db.setPort(port)
        self.db.setHostName(pg_connexion["host"])
        self.db.setUserName(pg_connexion["user"])
        self.db.setPassword(pg_connexion["password"])
        self.db.setDatabaseName(pg_connexion["database"])
        #set db to none if not open and schema and tables are not loaded
        if not self.db.open() or not self.check_schema_and_tables():
            self.db = None
        #set the indicator color according to status
        self._load_status()
        #return true/false
        return self.db is not None 

    def _load_status (self):
        """Set the color and text of the indicator according to the connection status."""
        if self.db:
            self.statusIndicator.setStyleSheet("background-color: rgb(0, 255, 0); border-radius: 5px;")
            self.statusConnection.setText("Connected : "+ self.db.databaseName())
        else:
            self.statusIndicator.setStyleSheet("background-color: rgb(255, 0, 0); border-radius: 5px;")
            self.statusConnection.setText("Not Connected")

    def close(self):
        """DBASE: Close the current database connection"""
        if self.db:
            self.db.close()
            del self.db
            self.db = None

    def exec(self, sql):
        """DBASE: Execute the provided SQL query and returns the result"""
        if self.db:
            return self.db.exec(sql)

    def last_error(self):
        """DBASE: Returns the last error that occurred in the database connection"""
        if self.db:
            return self.db.lastError()

    def dbname(self):
        """DBASE: Returns the name of the current database if it's open, otherwise `None`"""
        if self.db:
            return self.db.databaseName()
        
    def db_execute_sql(self, sql_query):
        """DBASE: Execute a sql query and return True or False if error"""
        result = self.db.exec(sql_query)
        return not result.lastError().isValid()

    def prepare(self, sql):
        """DBASE: Prepare a SQL query for the current database connection."""
        query = QtSql.QSqlQuery(self.db)
        #query.prepare(sql)
        if not query.prepare(sql):
            return None
        return query
    
    def postgres_error(self):
        """DBASE: Converts the last error in the database connection into a text string"""
        #convert the postgresl error in a text
        error = self.last_error()
        if error:
            tab_text = error.text().split("\n")
            return '\n'.join(tab_text[:3])

    def check_schema_and_tables(self):
        """DBASE: Checks if the schema and specific tables exist in the database. If not, create them with SQL scripts"""
        #block notice & infos msgs
        query = self.db.exec("SET client_min_messages = WARNING;")
        query.finish()

        #check if schema 'taxonomy' is available on the database
        dbschema = 'taxonomy'
        dbtables = ['taxa_reference', 'taxa_rank', 'taxa_nameset', 'taxa_wfo']
        sql_query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{dbschema}';"
        query = self.db.exec(sql_query)
        tables_list = []
        while query.next():
            tables_list.append(query.value("table_name"))
        result = all(item in tables_list for item in dbtables)
        if result:
            print ("Schema and Tables OK")
            return True
        else:
            print ("Error : Schema and/or tables are not present")
            #return False

    # Schema is not present, execute sql scripts to create tables, indexes, functions, triggers
            scripts = ['create_schema_taxonomy.sql','config_schema_taxonomy.sql']
            for script_path in scripts:
                file = QFile(f":src/florica/resources/sql/{script_path}")
                if not file.open(QFile.ReadOnly | QFile.Text):
                    raise RuntimeError(f"Error in opening : {script_path}")
                stream = QTextStream(file)
                stream.setCodec("UTF-8")
                sql = stream.readAll()
                self.exec(sql)
            return True

    def get_str_value(self, value):
        """
        Return the string representation of a database value, replacing NULL/None values by an empty string.
        """
        if value is None:
            return ""
        value = str(value).strip()
        if value.lower() in ("null", "none"):
            return ""
        return value

class PN_dbPlot:
    """ 
        A class for managing the plot database (plot schema) via a DatabaseConnection (composition).
        Methods and properties dedicated to plot management queries.
    """
#a subClass to manage the database of taxa (taxonomy schema), connexion with a DatabaseConnection (composition)
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self._dict_plot_properties = None
        self._ls_plot_columns = None

    @property
    def db_dict_strata (self):
        return {
        "understorey": [1, "sous-bois", "sotobosque", "understory"], 
        "sub-canopy": [2, "sous-canopée", "sub-cubierta"], 
        "canopy": [3, "canopée", "cubierta"], 
        "emergent": [4, "émergent","emergente"]
        }
    @property
    def db_dict_plot_properties(self):
        """DBASE: Returns a dictionary with default values for plot properties"""    
        if self._dict_plot_properties is None:
            self.refresh_db_dict_plot_properties()
        return self._dict_plot_properties
    
    @property
    def db_dic_plots(self):
        return {
            "id_plot" : {"type" : "integer", "enabled": False},
            "plot": {"type" : 'text', "tip": 'The name of the plot'},
            "type": {"type" : 'text', "editable": False, "items" : ["Circle", "Point", "Rectangle", "Transect"], "tip": 'The type of the plot'},
            "length": {"type" : 'numeric', "tip": 'The length of the plot', "min": 0, "max": 100000},
            "width": {"type" : 'numeric', "tip": 'The width or radius of the plot', "min": 0, "max": 100000},
            "azimuth": {"type" : "numeric", "unit": '°', "min": 0, "max": 360, "decimal": 2, "tip": 'The azimuth of the plot'},
            "dimension": {"type" : 'numeric', "enabled": False},
            "latitude": {"type" : "numeric", "unit": 'DD-WGS84', "min": -90, "max": 90, "decimal": 8, "tip": 'The latitude of the plot origin'},
            "longitude": {"type" : "numeric", "unit": 'DD-WGS84', "min": -180, "max": 180, "decimal": 8, "tip": 'The longitude of the plot origin'},
            "altitude": {"type" : 'numeric', "unit" : "m", "min": 0, "max": 10000, "decimal": 2, "tip": 'The altitude of the plot at origin'},           
            "x": {"type" : 'numeric', "min": 0,  "tip": 'X coordinate of the plant on the plot'}, 
            "y": {"type" : 'numeric', "min": 0,  "tip": 'Y coordinate of the plant on the plot'},
            "notes":  {"type" : 'memo', "tip": 'Some notes about the plot'}
            
        } | self.db_dict_plot_properties


    def refresh_db_dict_plot_properties(self):
        """Refreshes database-dependent plot properties."""

        #a dictionnary to describe the properties of a plot
        dict_properties = {
            "project": {"name" : {"type": "list", "items": "database"},
                        "collection": {"type" : 'list', "items": "database"},
                        "team" : {"type": "list", "items": "database"},
                        "owner" : {"type": "list", "items": "database"},
                        "notes" : {"type": "memo"}
                        },
            "locality" : {"name": {"type": "list", "items": "database"},
                          "site" : {"type": "text"},
                          "sector" : {"type": "text"},
                          "land" : {"type": "list", "editable": False, "items": ['Forest', 'Savanna', 'Grassland', 'Wetlands', 'Crop land']},
                          "habitat": {"type": "text"},                
            }
        }
        #Retrieve the tuple corresponding to the fields that need to be populated from the database.
        database_properties = []
        expressions = []
        for category, fields in dict_properties.items():
            for name, definition in fields.items():
                if definition.get("items") == "database":
                    database_properties.append((category, name))

                    path = f"{{{category},{name}}}"
                    alias = f"{category}_{name}"
                    expressions.append(
                    f"""
                    jsonb_agg(
                        DISTINCT properties #>> '{path}'
                        ORDER BY properties #>> '{path}'
                    ) FILTER (
                        WHERE properties #>> '{path}' IS NOT NULL
                    ) AS "{alias}"
                    """
                    )
        if expressions:
            sql_query = f"""
                SELECT {', '.join(expressions)}
                FROM plots.plots
            """
            query = self.db.exec(sql_query)
            if query.next():
                for i, (category, name) in enumerate(database_properties):
                    value = query.value(i)
                    if value:
                        dict_properties[category][name]["items"] = json.loads(value)
                    else:
                        dict_properties[category][name]["items"] = []
            query.finish()
            del query
        self._dict_plot_properties = dict_properties
        return self._dict_plot_properties


    # def get_distinct_property_values(self, properties):

    #     if not properties:
    #         return {}

    #     expressions = []

    #     for category, name in properties:
    #         path = f"{{{category},{name}}}"
    #         alias = f"{category}_{name}"

    #         expressions.append(
    #         f"""
    #         jsonb_agg(
    #             DISTINCT properties #>> '{path}'
    #             ORDER BY properties #>> '{path}'
    #         ) FILTER (
    #             WHERE properties #>> '{path}' IS NOT NULL
    #         ) AS "{alias}"
    #         """
    #         )

    #     sql_query = f"""
    #         SELECT {', '.join(expressions)}
    #         FROM plots.plots
    #     """

    #     query = self.db.exec(sql_query)
    #     if not query.next():
    #         return {}

    #     return {
    #         (category, name): query.value(i) or []
    #         for i, (category, name) in enumerate(properties)
    #     }

    @property
    def db_dic_traits(self):
        """DBASE: Returns a dictionary with default values for taxa properties"""
        #a dictionnary to describe the properties of a taxon

        return {
            "id_tree" : {"enabled": False, "type" : "integer"},
            "identifier":  {"type" : 'text', "tip": 'The unique identifier'},
            "taxaname" : {"type" : "text", "tip": 'The name of the taxa'},
            "year": {"type" : "integer", "max": datetime.now().year, "default": datetime.now().year, "tip": 'The year when the plant was observed'},
            "month": {"type" : "integer", "default":datetime.now().month, "items": functions.list_month, "tip": 'The month when the plant was observed'},
            "day": {"type" : "integer", "min": 1, "max": 31, "default":datetime.now().day, "tip": 'The day when the plant was observed'},
            "dead": {"type" : 'boolean', "default": False, "tip": 'Was the plant dead?'},
            "present": {"type" : 'boolean', "default": False, "tip": 'Has the plant been observed?'},
            "comments":  {"type" : 'memo',"synonyms" : ['comment', 'comments', 'commentaire', 'note'], "tip": 'Some comments about the observation'},

        #"structural": {
            "stems": {"type" : 'integer', "min": 1, "default":1, "tip": 'Number of stems at Breast Height [1m30]'},
        # },
        # "biometry" : {
            "dbh": {"type" : "numeric", "unit" : 'cm', "plot" :"hist", "min": 0, "max": 500, "tip": 'Diameter at Breast Height or 1m30 from the ground'},
            "height":  {"type" : "numeric", "unit" : 'm', "plot" :"hist", "min": 1, "max": 100, "tip": 'Height of the tree'},
        # },
        # "spatial" : {
            "strata": {"type" : "integer", "items": ["Understorey", "Sub-canopy", "Canopy", "Emergent"], "tip": 'Tree stratum in the vertical direction'},
        #     },
        # "phenology" : {
            "flower": {"type" : 'boolean', "tip": 'Is the plant flowering ?'}, 
            "fruit": {"type" : 'boolean', "tip": 'Is the plant fruiting ?'},
        #     },
        # "functional": {
            "bark_thickness": {"type" : "numeric", "unit" : 'mm', "plot" :"hist", "min": 1, "tip": 'Thickness of tree bark'},
            "leaf_area": {"type" : "numeric", "unit" : 'cm²', "plot" :"hist", "min": 0.01, "decimal": 5, "tip": 'Area of a leaf unit'},
            "leaf_sla": {"type" : "numeric", "unit" : 'mm²/mg', "plot" :"hist", "min": 1, "max": 50, "decimal": 5, "tip": 'Specific Leaf Area'},
            "leaf_ldmc": {"type" : "numeric", "unit" : 'mg/g', "plot" :"hist", "min": 10, "max": 1000, "tip": 'Leaf Dry Matter Content'},
            "leaf_thickness": {"type" : "numeric", "unit" : 'µm', "plot" :"hist", "min":10, "max": 1000, "tip": 'Thickness of the leaf'},
            "wood_density": {"type" : "numeric", "unit" : 'g/cm3', "plot" :"hist", "min": 0.1, "max": 2, "decimal": 5, "tip": 'Density of a wood core'},
            "leaf_dry_weight": {"type" : "numeric", "unit" : 'mg', "plot" :"hist", "min": 1, "max": 100000, "decimal": 2, "tip": 'Weight of a dry leaf unit'},
            "leaf_fresh_weight": {"type" : "numeric", "unit" : 'mg', "plot" :"hist", "min": 10, "decimal": 2, "tip": 'Weight of a fresh leaf unit'},
            "wood_core_diameter": {"type" : "numeric", "unit" : 'mm', "plot" :"hist", "decimal": 3, "tip": 'Diameter of the wood core'},
            "wood_core_length": {"type" : "numeric", "unit" : 'mm', "plot" :"hist", "decimal": 3, "tip": 'Length of the wood core'},
            "wood_core_weight": {"type" : "numeric", "unit" : 'mg', "plot" :"hist", "decimal": 3, "tip": 'Dry weight of the wood core'}
            # },
            }
    @property
    def db_dic_plot_filter(self):
        """DBASE: Returns a dictionary with default values for filtering plots from the database"""
        return  {"id_plots" : None, 
                    "search_plot": None, 
                    # "collection": None, 
                    "type_plot": None,
                    "properties": None
                    }

    @property
    def db_dic_tree_filter(self):
        """DBASE: Returns a dictionary with default values for filtering trees from the database"""
        return  {"id_tree" : None, 
                    "identifier": None, 
                    "taxaname": None,
                    "id_plot": None,
                    "properties": None
                }

    def db_get_json_tree_properties(self, id_tree, id_plot = None):
        """DBASE: Returns the properties of a tree in the database as a JSON object"""

        # Create the SQL filter for id_plot if provided
        sql_plot = ""
        if id_plot is not None:
            sql_plot = f"AND b.id_plot = {id_plot}"

        #create the final sql_query
        sql_query = f"""
            SELECT jsonb_agg(
                to_jsonb(a)
                ORDER BY a.year DESC, a.month DESC NULLS LAST, a.day DESC NULLS LAST
            ) AS data
            FROM plots.trees_observation a
            INNER JOIN plots.trees_plot b ON a.id_tree = b.id_tree
            WHERE b.id_tree = {id_tree}
            {sql_plot};                    
            """
                
        #execute the sql_query
        #print (sql_query)
        history = {}
        observations = []

        query = self.db.exec(sql_query)
        if query.next():
            data = query.value("data")
            if data is not None:
                data = json.loads(data)     
                observations = self.fill_templates_from_jsonRows(data, self.db_dic_traits)

                # Construct the history dictionaries from the observations
                for row in observations[::-1]:
                    for key, value in row.items():
                        if key in ['id_tree', 'year', 'month', 'day']:
                            continue
                        if value is not None:
                            history.setdefault(key, []).append(
                                f"{row['year']}:\t{value}"
                            )
        query.finish()
        return observations, history                    
        
        # for row in result[::-1]:
            
        #     properties = dict(row["properties"] or {})
        #     properties["dead"] = row["dead"]
        #     properties["present"] = row["present"]
            
        #     #crzeate the historical hierarchy
        #     for key, value in properties.items():
        #         row[key] = value
        #         v_translate = self.db.db_translate(value,field_trees[key])
        #         history.setdefault(key, []).append(
        #             f"{row['year']}:\t{v_translate}"
        #         )

        # Order plots according to field_plots
        # plots = {
        #     key: plots[key] 
        #     for key in field_plots 
        #     if key in plots
        # }
        # Order history according to field_trees            
        # history = {
        #     key: history[key]
        #     for key in field_trees
        #     if key in history
        # }

        #Insert the current observation at index 0
        #observations.insert(0, current)
        query.finish()
        del query
        return observations, history



    def db_get_json_trees (self, dict_filter = None):
        """DBASE: Return the latest tree observation data as compact dict rows.
           Includes latest non-null trait values (identifier, taxaname, stems) and latest dead/present/time_updated values.
        """
        tab_sql = []
        sql_where = ''
        #print (dict_filter)
        if dict_filter:
            _idplots = dict_filter.get("id_plots", [])
            _idplots = _idplots if isinstance(_idplots, list) else [_idplots]
            if _idplots:
                #tab_sql.append(f"id_plot IN ({','.join(str(id) for id in _idplots)})")
                tab_sql.append(f"id_plot = ANY (ARRAY{_idplots})")


            tab_properties = dict_filter.get("properties", {})
            if tab_properties is None:
                tab_properties = {}
            for key, value in tab_properties.items():
                for key2, value2 in value.items():
                    if value2:
                        data = {key: {key2: value2}}
                        _prop = f"(properties @> '{json.dumps(data)}')"
                        _prop = f"(properties -> '{key}' ->> '{key2}' = '{value2.lower()}')"
                        tab_sql.append(_prop)

        if tab_sql:
            sql_where = "WHERE " + " AND ".join(tab_sql)
        
        sql_query = f"""
            SELECT 
                row_to_json(a) current, 
                b.properties 
            FROM 
                (SELECT DISTINCT ON (o.id_tree)
                    o.id_tree,
                    t.id_plot, t.x, t.y, o.comments, o.dead, o.present, --o.time_updated,
                    o.year::text
                    || COALESCE(lpad(o.month::text, 2, '0'), '')
                    || COALESCE(lpad(o.day::text, 2, '0'), '') AS date_obs
                FROM 
                    plots.trees_plot t
                INNER JOIN 
                    plots.trees_observation o ON t.id_tree = o.id_tree
                {sql_where}
                ORDER BY 
                    o.id_tree, date_obs DESC
                ) a
            LEFT JOIN 	
                (SELECT 
                    id_tree, 
                    json_agg(properties ORDER BY id_tree, make_date(o.year, COALESCE(o.month, 1)::integer, COALESCE(o.day, 1)::integer) ) AS properties
                FROM 
                    plots.trees_observation o
                WHERE 
                    properties IS NOT null
                GROUP BY 
                    id_tree
                ) b
            ON a.id_tree = b.id_tree
        """

        sql_query = f"""
            SELECT 
                a.data, 
                b.properties 
            FROM 
                (SELECT DISTINCT ON (o.id_tree)
                	o.id_tree,
            	jsonb_build_array(
                    t.id_plot, t.x, t.y, 
                    o.id_tree,
                    o.dead, 
                    o.present,
                    o.year::text,
                    o.month::text,
                    o.day::text,
                    o.comments
                    ) AS data
                FROM 
                    plots.trees_plot t
                INNER JOIN 
                    plots.trees_observation o ON t.id_tree = o.id_tree
                {sql_where}
                ORDER BY 
                    o.id_tree, 
                    o.year::text
                    || COALESCE(lpad(o.month::text, 2, '0'), '')
                    || COALESCE(lpad(o.day::text, 2, '0'), '')
                DESC
                ) a
            LEFT JOIN 	
                (SELECT 
                    id_tree, 
                    json_agg(properties ORDER BY id_tree, make_date(o.year, COALESCE(o.month, 1)::integer, COALESCE(o.day, 1)::integer) ) AS properties
                FROM 
                    plots.trees_observation o
                WHERE 
                    properties IS NOT null
                GROUP BY 
                    id_tree
                ) b
            ON a.id_tree = b.id_tree
        """

        query = self.db.exec(sql_query)
        trees = []
        rows = []
        _columns= ["id_plot", "x", "y", "id_tree", "dead", "present", "year", "month", "day", "comments"]
        while query.next():
            data = json.loads(query.value("data"))
            data = dict(zip(_columns, data))

            month = data["month"]
            day = data["day"]
            year = data["year"]
            date_str = year
            if month:
                date_str = f"{month.zfill(2)}/{year}"
            if day:
                date_str = f"{day.zfill(2)}/{month.zfill(2)}/{year}"

            data["date_obs"] = date_str


            # date_obs = str(data["year"])
            # if data["month"] is not None:
            #     date_obs += data["month"].zfill(2)
            # if data["day"] is not None:
            #     date_obs += data["day"].zfill(2)
            # data["date_obs"] = date_obs


            traits = json.loads(query.value("properties"))
            obs = {}
            for trait in traits:
                obs.update(trait)
            data["properties"] = obs
            rows.append(data)

        trees = self.fill_templates_from_jsonRows(rows, self.db_dic_traits)
        return trees

    

        #transform in json
        data = [
            dict(zip(self._ls_plot_columns, row))
            for row in rows
        ]




        while query.next():
            observation = query.value("current")
            if isinstance(observation, str):
                observation = json.loads(observation)
            # observation["taxaname"] = None
            # observation["stems"] = None
            # observation["fruit"] = None
            # observation["flower"] = None

            obs = {}
            traits = query.value("properties")
            if isinstance(traits, str):
                traits = json.loads(traits)
            for trait in traits:
                obs.update(trait)
            #observation.update(obs)
            #id_plot = observation.get("id_plot")
            observation["properties"] = obs
            observation = self.fill_templates_from_jsonRows([observation], self.db_dic_traits)
            #observation[0]["id_plot"]=id_plot


            trees += observation
            
        #     trees.append(observation)
        # trees = self.fill_templates_from_jsonRows(trees, self.db_dic_traits)
        return trees
            
    # def db_get_json_trees_old (self, dict_filter = None):
    #     """DBASE: Return the latest tree observation data as compact dict rows.
    #        Includes latest non-null trait values (identifier, taxaname, stems) and latest dead/present/time_updated values.
    #     """
    #     tab_sql = []
    #     sql_where = ''
    #     #print (dict_filter)
    #     if dict_filter:
    #         _idplots = dict_filter.get("id_plots", [])
    #         _idplots = _idplots if isinstance(_idplots, list) else [_idplots]
    #         if _idplots:
    #             #tab_sql.append(f"id_plot IN ({','.join(str(id) for id in _idplots)})")
    #             tab_sql.append(f"id_plot = ANY (ARRAY{_idplots})")


    #         tab_properties = dict_filter.get("properties", {})
    #         if tab_properties is None:
    #             tab_properties = {}
    #         for key, value in tab_properties.items():
    #             for key2, value2 in value.items():
    #                 if value2:
    #                     data = {key: {key2: value2}}
    #                     _prop = f"(traits @> '{json.dumps(data)}')"
    #                     _prop = f"(traits -> '{key}' ->> '{key2}' = '{value2.lower()}')"
    #                     tab_sql.append(_prop)

    #     if tab_sql:
    #         sql_where = "WHERE " + " AND ".join(tab_sql)
    # #create the sql_query
    #     sql_query = f"""
    #         WITH obs AS (
    #             SELECT
    #                 t.id_tree,
    #                 t.id_plot,
    #                 t.x,
    #                 t.y,
    #                 o.traits ->> 'identifier' AS identifier,
    #                 o.traits ->> 'taxaname' AS taxaname,
    #                 (o.traits ->> 'stems')::integer AS stems,
    #                 (o.traits ->> 'flower')::boolean AS flower,
    #                 (o.traits ->> 'fruit')::boolean AS fruit,
    #                 o.dead::boolean,
    #                 o.present::boolean,
    #                 o.time_updated,
    #                 make_date(o.year, COALESCE(o.month, 1)::integer, COALESCE(o.day, 1)::integer) AS sort_date
    #             FROM plots.trees_plot t
    #             INNER JOIN plots.trees_observation o ON t.id_tree = o.id_tree
    #             {sql_where}
    #         ),
    #         aggregated_obs AS (
    #             SELECT
    #                 id_tree,
    #                 id_plot,
    #                 x,y,
    #                 -- Fusion des valeurs les plus récentes non nulles
    #                 (array_remove(array_agg(identifier ORDER BY sort_date DESC), NULL))[1] AS current_identifier,
    #                 (array_remove(array_agg(taxaname   ORDER BY sort_date DESC), NULL))[1] AS current_taxaname,
    #                 (array_remove(array_agg(stems      ORDER BY sort_date DESC), NULL))[1] AS current_stems,
    #                 (array_remove(array_agg(flower      ORDER BY sort_date DESC), NULL))[1] AS current_flower,
    #                 (array_remove(array_agg(fruit      ORDER BY sort_date DESC), NULL))[1] AS current_fruit,
    #                 -- Dernières valeurs absolues
    #                 (array_agg(time_updated ORDER BY sort_date DESC))[1] AS current_date,
    #                 (array_agg(dead         ORDER BY sort_date DESC))[1] AS current_dead,
    #                 (array_agg(present      ORDER BY sort_date DESC))[1] AS current_present
    #             FROM obs
    #             GROUP BY id_tree, id_plot, x, y
    #         )
    #         SELECT 
    #             --json_build_object(
    #             --'fields', json_build_array('id_tree', 'identifier', 'taxaname', 'stems', 'time_updated', 'dead', 'present', 'id_plot'),
    #             --'rows', 
    #             COALESCE(
    #                 json_agg(
    #                     json_build_array(
    #                         c.id_tree,
    #                         c.current_identifier,
    #                         c.current_taxaname,
    #                         c.current_stems,
    #                         c.current_flower,
    #                         c.current_fruit,
    #                         c.current_date,
    #                         c.current_dead,
    #                         c.current_present,
    #                         c.id_plot,
    #                         c.x, c.y
    #                     )
    #                 ),
    #                 '[]'::json
    #             )
    #         --) 
    #         AS data
    #         FROM aggregated_obs c;
    #     """        
        
    #     #execute the query
    #     #print (sql_query)
    #     query = self.db.exec(sql_query)
    #     json_list = []
    #     if query.next():
    #         result = query.value("data")
    #         if result:
    #             _rows = json.loads(result)
    #             if _rows:
    #                 _fields = ['id_tree', 'identifier', 'taxaname', 'stems', 'flower', 'fruit', 'time_updated', 'dead', 'present', 'id_plot', 'x', 'y']
    #                 json_list = [
    #                     dict(zip(_fields, row))
    #                     for row in _rows
    #                 ]
    #     query.finish() 
    #     del query
    #     return json_list

    

    def db_get_json_plots(self, dict_filter = None):
        """DBASE: Returns a list of plots in the database as a JSON object"""
        tab_sql = []
        sql_where = ''
        if dict_filter:
        #31) filter on plot name
            txt_search = dict_filter.get("search_plot", '')
            if txt_search:
                tab_sql.append(f"plot ILIKE '%{txt_search}%'")

        #2) filter on plot type
            type_plot = dict_filter.get("type_plot", '')
            if type_plot:
                tab_sql.append(f"type = '{type_plot}'")

        #2) filter on properties
            tab_properties = dict_filter.get("properties", {})
            if tab_properties:
                for key, value in tab_properties.items():
                    for key2, value2 in value.items():
                        if value2:
                            if "%" in str(value2):
                                _prop = (
                                    f"(properties -> '{key}' ->> '{key2}' "
                                    f"ILIKE '{value2}')"
                                )
                            else:
                                data = {key: {key2: value2}}
                                _prop = f"(properties @> '{json.dumps(data)}')"
                            tab_sql.append(_prop)

        #get the sql_where filter if any filter is applied
        if tab_sql:
            sql_where = "WHERE " + " AND ".join(tab_sql)

        #create the final sql_query
        # sql_query = f"""
        #         SELECT
        #         jsonb_agg(
        #                 to_json(t)
        #                 ORDER BY t.plot
        #                 ) data
        #         FROM plots.plots t
        #         {sql_where}
        #         """

        # sql_query = f"""SELECT t.*
        #                 FROM plots.plots t
        #                 {sql_where}                        
        #                 ORDER BY t.plot
        #             """




        #gets the column names from the database if not already cached, use columns instead of * to conserve type 
        if self._ls_plot_columns is None:
            sql_query = f"""
                SELECT jsonb_agg(column_name ORDER BY ordinal_position) columns
                FROM information_schema.columns
                WHERE table_schema = 'plots'
                AND table_name = 'plots'"""
            query = self.db.exec(sql_query)
            if query.next():
                self._ls_plot_columns = json.loads(query.value("columns"))

        #create the final sql_query
        columns_sql = ", ".join(self._ls_plot_columns)

        sql_query = f"""
             SELECT
                jsonb_build_array(
					{columns_sql}
                ) data
                FROM plots.plots t
                {sql_where}
                ORDER BY t.plot;"""

        
        #execute the query
        json_list = []
        query = self.db.exec(sql_query)




        


                #get the rows
        rows = []
        while query.next():
            data = json.loads(query.value("data"))
            #row = dict(zip(columns, data))
            rows.append(data)

            #transform in json
        data = [
            dict(zip(self._ls_plot_columns, row))
            for row in rows
        ]





        #get the columns
        # record = query.record()
        # columns = []
        # columns = [
        #     record.fieldName(i)
        #     for i in range(record.count())
        # ]
        # #get the rows
        # rows = []
        # while query.next():
        #     rows.append([
        #         query.value(i)
        #         for i in range(record.count())
        #     ])
        # #transform in json
        # data = [
        #     dict(zip(columns, row))
        #     for row in rows
        # ]

        #manage the field dimension according to the plot type
        for plot in data:
            _type = plot.get("type", "").lower()
            if _type == 'rectangle':
                dimension = (plot.get("width", 0) * plot.get("length", 0)) / 1E4
            elif _type == 'circle':
                dimension = (3.141592654 * plot.get("width", 0)**2) / 1E4
            elif _type == 'transect':
                dimension = plot.get("length", 0)
            else:
                dimension = None
            if dimension:
                dimension = round(dimension, 2)
                if dimension.is_integer():
                    dimension = int(dimension)
                if _type == 'transect':
                    dimension = f"{dimension} m"
                else:
                    dimension = f"{dimension} ha"
            plot ["dimension"] = dimension
            
        #Fill json according to the plot template dictionary
        json_list = self.fill_templates_from_jsonRows(data, self.db_dic_plots)

        query.finish() 
        return json_list

                                        
        # while query.next():
        #     result = query.value("data")


        #     result = json.loads(result) if result else []
        #     json_list = self.fill_templates_from_jsonRows(result, self.db_dic_plots)

        if query.next():
            result = query.value("data")
            data = json.loads(result) if result else []
            #manage the field dimension according to the plot type
            for plot in data:
                _type = plot.get("type", "").lower()
                if _type == 'rectangle':
                    dimension = (plot.get("width", 0) * plot.get("length", 0)) / 1E4
                elif _type == 'circle':
                    dimension = (3.141592654 * plot.get("width", 0)**2) / 1E4
                elif _type == 'transect':
                    dimension = plot.get("length", 0)
                else:
                    dimension = None
                if dimension:
                    dimension = round(dimension, 2)
                    if dimension.is_integer():
                        dimension = int(dimension)
                    if _type == 'transect':
                        dimension = f"{dimension} m"
                    else:
                        dimension = f"{dimension} ha"
                plot["dimension"] = dimension
            #Fill json according to the plot template dictionary
            json_list = self.fill_templates_from_jsonRows(data, self.db_dic_plots)
            
        query.finish() 
        return json_list

    # def json_default (self, obj):
    #     if isinstance(obj, QtCore.QDate):
    #         return obj.toString("yyyy-MM-dd")
    #     if isinstance(obj, QtCore.QDateTime):
    #         return obj.toString(QtCore.Qt.ISODate)
    #     if isinstance(obj, QtCore.QTime):
    #         return obj.toString("HH:mm:ss")
    #     raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")        

    def fill_templates_from_jsonRows(self, queries, dict_fieldDefs):
        """
    
        """
        template = self.db.create_template(dict_fieldDefs)   
        results = []



        for row in queries:

            # Récupération du JSONB
            properties = {}
            if "properties" in row:
                properties = row.get("properties") or {}

            # Selon la source, le JSONB peut être retourné
            # comme str plutôt que comme dict.
            if isinstance(properties, str):
                try:
                    properties = json.loads(properties)
                except (json.JSONDecodeError, TypeError):
                    properties = {}

            if not isinstance(properties, dict):
                properties = {}

            result = deepcopy(template)
            for key, value in row.items():
                if key != "properties" and key not in result:
                    result[key] = value

            def fill(node, properties_data, _fieldDefs):
                for key, value in node.items():

                    if isinstance(value, dict):
                        sub_data = properties_data.get(key, {})
                        sub_fieldDefs = _fieldDefs.get(key, {})
                        if isinstance(sub_data, dict):
                            fill(value, sub_data, sub_fieldDefs)
                    else:
                        # validate _value acording to the type defined in _fieldDefs
                        if key in row:
                            _value = row[key]
                        else:
                            _value = properties_data.get(key)
                        if isinstance(_value, QtCore.QDate):
                            _value = _value.toString("yyyy-MM-dd")
                        if key in _fieldDefs:
                            _value = self.db.db_translate(_value, _fieldDefs[key])
                        # if _value is None:
                        #     _value =''

                        node[key] = _value


            fill(result, properties, dict_fieldDefs)

            results.append(result)

        return results




    def fill_templates_from_query(self, query, template):
        """
        Lit toutes les lignes d'un QSqlQuery et remplit une copie du template
        pour chaque ligne.

        Les valeurs sont recherchées :
        1. dans les colonnes SQL ;
        2. dans le JSONB 'properties' pour les champs imbriqués.

        Les valeurs absentes ou NULL restent à None.

        Returns:
            list[dict]: Une liste de dictionnaires correspondant aux lignes SQL.
        """

        record = query.record()

        # Noms des colonnes disponibles dans le résultat SQL
        field_names = [
            record.fieldName(i)
            for i in range(record.count())
        ]

        results = []

        while query.next():

            # Conversion automatique de la ligne QSqlQuery en dict
            row = {
                field_name: query.value(i)
                for i, field_name in enumerate(field_names)
            }

            # Récupération du JSONB
            properties = row.get("properties") or {}

            # Selon le driver Qt/PostgreSQL, le JSONB peut être retourné
            # comme str plutôt que comme dict.
            if isinstance(properties, str):
                try:
                    properties = json.loads(properties)
                except (json.JSONDecodeError, TypeError):
                    properties = {}

            if not isinstance(properties, dict):
                properties = {}

            result = deepcopy(template)

            def fill(node, properties_data):
                for key, value in node.items():

                    if isinstance(value, dict):
                        sub_data = properties_data.get(key, {})

                        if isinstance(sub_data, dict):
                            fill(value, sub_data)

                    else:
                        # Les colonnes SQL sont prioritaires
                        if key in row:
                            node[key] = row[key]
                        else:
                            node[key] = properties_data.get(key)

            fill(result, properties)

            results.append(result)

        return results


    
class PN_dbTaxa:
    """ 
        A class for managing the taxon database (taxonomy schema) via a DatabaseConnection (composition).
        Methods and properties dedicated to taxon management queries.
    """
#a subClass to manage the database of taxa (taxonomy schema), connexion with a DatabaseConnection (composition)
    def __init__(self, db: DatabaseConnection):
        self.db = db
        self.rank_typology = None
        self.ls_taxa_groups = None


#############################
    @property
    def db_dic_filter(self):
        """DBASE: Returns a dictionary with default values for filtering taxa from the database"""
        return  {"id_taxonref" : None, 
                       "search_name": None, 
                       "clade": None, 
                       "properties": None
                }
    @property
    def db_dic_properties(self):
        """DBASE: Returns a dictionary with default values for taxa properties"""
        #a dictionnary to describe the properties of a taxon
        return {
            "leaf" : {"type": {"type": "list", "items": ['Simple', 'Compound', 'Phyllode']}, 
                    "phyllotaxy": {"type": "list", "items": ['Alternate', 'Opposite', 'Verticillate']}, 
                    "stipulate": {"type": 'boolean'}
                    },
            "habit": {"epiphyte": {"type": 'boolean'},
                        "herbaceous": {"type": 'boolean'},
                        "liana": {"type": 'boolean'},
                        "parasite": {"type": 'boolean'},
                        "shrub": {"type": 'boolean'},
                        "tree": {"type": 'boolean'}
                    },
            "sexual": {"dioecious": {"type": 'boolean'},
                        "hermaphrodite": {"type": 'boolean'},
                        "fleshy fruit": {"type": 'boolean'}, 
                        "dispersal unit": {"type": 'list', "items": ['Seed', 'Fruit']}
                    },
            "architecture": {"model": {"type": 'list', "items": ['Attims','Aubreville','Chamberlain','Champagnat','Cook','Corner','Fagerlind','Holtum','Koriba','Leuwenberg','Mangenot','Massart','McClure','Nozeran','Petit','Prevost','Rauh','Roux','Scarrone','Schoute','Stone','Tomlinson','Troll']},
                            "monocaulous": {"type": 'boolean'},
                            "cauliflorous": {"type": 'boolean'}, 
                            "rythmic growth": {"type": 'boolean'}
                    },
            "disperser": {"anemochory": {"type": 'boolean'}, 
                            "barochory": {"type": 'boolean'}, 
                            "entomochory": {"type": 'boolean'}, 
                            "ornitochory": {"type": 'boolean'}, 
                            "myrmecochory": {"type": 'boolean'}, 
                            "saurochory": {"type": 'boolean'},
                            "zoochorie": {"type": 'boolean'}
                    },
            "new caledonia": {"status": {"type": 'list', "items": ['Endemic','Autochtonous','Introduced']}
                    }
            }
    
    def db_get_value(self, field_name, id_taxonref):
        """DBASE: Returns the value of field_name for id_taxonref in the taxa_reference table"""
        sql_query = f"""
                    SELECT 
                        {field_name} 
                    FROM
                        taxonomy.taxa_reference
                    WHERE
                        id_taxonref = {id_taxonref}
                   """
        #execute the query
        query = self.db.exec(sql_query)
        value = None
        if query.next():
            value = query.value(field_name)
        query.finish()
        del query
        return value
    

    
    def db_add_synonym(self, id_taxonref, synonym, category = 'Orthographic'):
        """DBASE: Add a synonym to a id_taxonref, return True or False if error"""
        sql_query = f"SELECT taxonomy.pn_names_add ({id_taxonref}, '{synonym}', '{category}')"
        #execute the query
        return self.db_execute_sql(sql_query)
    
    def db_add_synonyms(self, id_taxonref, ls_synonyms):
        """DBASE: Add a list of synonyms to an id_taxonref, return inserted count or -1 if error"""

        sql_query = """
            SELECT taxonomy.pn_names_add_batch(?, ?::text[])
        """

        query = self.db.prepare(sql_query)

        query.addBindValue(id_taxonref)

        # Conversion liste Python -> tableau PostgreSQL
        pg_array = "{" + ",".join(
            f'"{s.replace("\\", "\\\\").replace(chr(34), "\\" + chr(34))}"'
            for s in ls_synonyms
        ) + "}"

        query.addBindValue(pg_array)

        if not query.exec():
            print(query.lastError().text())
            return -1

        if query.next():
            return query.value(0)

        return 0
    
    def db_edit_synonym(self, old_synonym, new_synonym, new_category = 'Orthographic'):
        """DBASE: Update a name/category of asynonym, return True or False if error"""
        sql_query = f"SELECT taxonomy.pn_names_update ('{old_synonym}','{new_synonym}', '{new_category}')"
        #execute the query
        return self.db_execute_sql(sql_query)

    def db_delete_synonym(self, synonym):
        """DBASE: Delete a synonym, returns True or False in case of error"""
        sql_query = f"SELECT taxonomy.pn_names_delete ('{synonym}')"
        #execute the query
        return self.db_execute_sql(sql_query)
    
    def db_update_properties (self, id_taxonref, json_properties):
        """DBASE: Update the properties field of an id_taxonref with a json string, return True or False if error"""
        _idrankspecies = self.db_get_rank('species', 'id_rank')
        if json_properties is None:
            json_properties = 'NULL'
        else:
            json_properties = json_properties.replace("'", "''")  # escape single quotes
            json_properties = f"'{json_properties}'::jsonb"
        sql_query = f"""UPDATE taxonomy.taxa_reference 
                        SET properties = {json_properties}
                        WHERE id_taxonref = {id_taxonref} 
                        AND id_rank >= {_idrankspecies};
                    """
        #execute the query
        return self.db_execute_sql(sql_query)
    
    def db_update_metadata (self, id_taxonref, json_metadata):
        """DBASE: Update the metadata field on an id_taxonref with a json string, return True or False if error"""
        if json_metadata is None:
            json_metadata = 'NULL'
        else:
            json_metadata = json_metadata.replace("'", "''")  # escape single quotes
            json_metadata = f"'{json_metadata}'::jsonb"
        sql_query = f"""UPDATE taxonomy.taxa_reference 
                        SET metadata = {json_metadata}
                        WHERE id_taxonref = {id_taxonref};
                    """
        #execute the query
        return self.db_execute_sql(sql_query)
    
    def db_merge_reference (self, from_idtaxonref, to_idtaxonref, category='Orthographic'):
        """DBASE: Merging two taxa, from_idtaxonref becomes a synonym for to_idtaxonref"""
        if to_idtaxonref == from_idtaxonref:
            return False
        sql_query = f"CALL taxonomy.pn_taxa_set_synonymy({from_idtaxonref}, {to_idtaxonref}, '{category}');"
        #execute the query
        return self.db_execute_sql(sql_query)
    


##############################
    def db_get_rank(self, key, field_name = None):
        """DBASE: Returns a value for a rank key (id_rank or rank_name) according to a field_name, all  value if field_name is None"""
    #set the global dictionnary of rank typology if not exists and returns the dictionnary of a rank from its id_rank or rank_name
        #create a query to copy the table taxonomy.taxa_rank in a dictionnary
        if self.rank_typology is None:
            sql_query = """
                SELECT id_rank, rank_name, row_to_json(t) json_row 
                FROM 
                    (SELECT id_rank, rank_name, id_rankparent, suffix, prefix, childs
                    FROM taxonomy.taxa_rank a,
                    LATERAL 
                        (SELECT
                            to_json(array_agg(id_rank)) AS childs
                        FROM
                            taxonomy.pn_ranks_children(a.id_rank) b
                        ) z
                    ) t
                ORDER BY 
                    id_rank
            """
        #execute the query
            query = self.db.exec(sql_query)
            self.rank_typology = {}
        #fill the dictionnary with a both entries: id_rank and rank_name as key
            while query.next():
                self.rank_typology[query.value("id_rank")] = json.loads(query.value("json_row"))
                self.rank_typology[query.value("rank_name")] = json.loads(query.value("json_row"))

            query.finish()
            del query
        #ensure that the key is in lowercase (error and nothin if numerci)
        try:
            key = key.lower()
        except:
            pass
    #return for the rank (key), the dictionary and field value if field is not None
        if key == "all":
            return self.rank_typology.copy()

        if key in self.rank_typology:
            if field_name is None:
                return self.rank_typology[key].copy()
            else:
                return self.rank_typology[key][field_name]
        return None
    
    def db_get_searchnames (self, ls_search_name):
        """DBASE: Returns a dictionary {"taxaname": id_taxonref} of names found in the database from a list of taxaname (ls_search_name)"""
        #ex: return {"Amborella": 300, "Amborella trichopoda": 1802} from a the list ['Amborella', 'Amborella trichopoda', 'Miconia foo']
        sql_query = f"""
                    SELECT 
                        jsonb_object_agg(original_name, id_taxonref)
                    FROM 
                        taxonomy.pn_taxa_searchnames(ARRAY{ls_search_name})
                    WHERE 
                        id_taxonref IS NOT NULL;
                    """
        #execute the query
        query = self.db.exec(sql_query)
        json_list ={}
        if query.next():
            result = query.value(0)
            if result:
                json_list = json.loads(result)
        query.finish() 
        del query
        return json_list
    
    def db_get_fuzzynames(self, search_name, score = 0.4):
        """DBASE: Returns a dictionary of names found in the database from a fuzzy name (search_name)
            #ex: {'Amborella trichopoda Baill.': {"id_taxonref": 1802, "score": 0.95, "synonym": ['Amborella trichopodo', 'Amborella']}, ...}
        """
        if len(search_name) < 4:
            return
        if len(search_name) < 8:
            score = 0.2
        #create sql query
        sql_query = f"""
            SELECT 
                a.taxonref, a.score, a.id_taxonref, json_agg(DISTINCT c.name ORDER BY c.name) AS synonym
            FROM 
                taxonomy.pn_taxa_searchname('{search_name}', {score}::numeric) a 
            LEFT JOIN 
                taxonomy.taxa_nameset c 
            ON 
                a.id_taxonref = c.id_taxonref AND c.category <> 1
            GROUP BY a.taxonref, a.score, a.id_taxonref
            ORDER 
                BY score DESC
        """
        #execute sql_query and return json result
        query = self.db.exec(sql_query)
        dict_db_names = {}
        while query.next():
            dict_db_names[query.value("taxonref")] = {
                "id_taxonref": query.value("id_taxonref"),
                "score": query.value("score"),
                "synonym": json.loads(query.value("synonym"))
            }
        query.finish()
        del query
        return dict_db_names

       
    def db_get_valid_merges (self, id_taxonref):
        """DBASE: Returns a dictionary {"name": id_taxonref} of valid sibling taxa for merging taxa based on their rank"""
            #ex: return {'Acorales': 17056, 'Alismatales': 17057, 'Amborellales': 16183,...}, when searching for a order
        _idrankspecies = self.db_get_rank('species', 'id_rank')
        sql_query = f"""
                    SELECT
                    n.taxaname, n.id_taxonref
                    FROM taxonomy.taxa_names n
                    JOIN taxonomy.taxa_reference r ON r.id_taxonref = {id_taxonref}
                    WHERE
                        (r.id_rank < {_idrankspecies} AND n.id_rank = r.id_rank)
                        OR
                        (r.id_rank >= {_idrankspecies} AND n.id_rank >= {_idrankspecies})
                    ORDER BY n.taxaname;
                    """
        #execute the query
        query = self.db.exec(sql_query)
        taxa_dict = {}
        while query.next():
            taxa_dict[query.value(0)] = query.value(1)
        query.finish()  
        del query
        return taxa_dict
    
    def db_get_valid_parents (self, id_taxonref):
        """DBASE: Returns a dictionary {"name": id_taxonref} of valid parents taxa for moving taxa based on their rank"""
            #ex: return {'Acorales': 17056, 'Alismatales': 17057, 'Amborellales': 16183,...}, when searching for a family

        sql_query = f"""
                SELECT
                n.taxaname,                 n.id_taxonref
                FROM taxonomy.taxa_names n
                JOIN taxonomy.taxa_reference r ON r.id_taxonref = {id_taxonref}
                JOIN taxonomy.taxa_rank tr ON r.id_rank = tr.id_rank
                WHERE
                    n.id_rank >= tr.id_rankparent
                AND n.id_rank < tr.id_rank
                ORDER BY n.taxaname;
                """
        #execute the query
        query = self.db.exec(sql_query)
        taxa_dict = {}
        while query.next():
            taxa_dict[query.value(0)] = query.value(1)
        query.finish()  
        del query
        return taxa_dict


    def db_get_childs (self, ls_idtaxonref):
        """
            DBASE: Returns a list of id_taxonref childs from a list of id_taxonref
        """
        if not isinstance(ls_idtaxonref, list):
            ls_idtaxonref = [ls_idtaxonref]
        ls_idtaxonref = ",".join(map(str, ls_idtaxonref))
        sql_query = f"""
                SELECT DISTINCT
                taxonomy.pn_taxa_childs(id_taxonref, True) id_taxonref
                FROM taxonomy.taxa_reference
                WHERE id_taxonref IN ({ls_idtaxonref});
        """
                                               
        #execute the query
        query = self.db.exec(sql_query)
        ls_childs = []
        while query.next():
            ls_childs.append(query.value(0))
        query.finish()  
        del query
        return ls_childs
    
    
    def db_get_names(self, id_taxonref):
        """DBASE: Returns a dictionary  names associated to a id_taxonref, grouped by categories"""
        #ex: {'Autonyms': ['Amborella trichopoda Baill.', 'Amborella trichopoda'], 'Homotypic': ['Platyspermation crassifolium', 'Platyspermation crassifolium Guillaumin']}
        sql_query = f"""
                    SELECT 
                        a.name,  a.category, a.id_category 
                    FROM 
                        taxonomy.pn_names_items({id_taxonref}) a 
                    ORDER BY 
                        a.id_category, a.name
                    """
        #execute the query
        query = self.db.exec(sql_query)
        dict_db_names = {'Autonyms': []} #to ensure the first row
        while query.next():
            #groups any name by category
            if query.value("id_category") < 5:
                _category = 'Autonyms'
            else:
                _category = query.value("category")
            #add category to the final result if not exists
            if _category not in dict_db_names:
                dict_db_names[_category] = []
            dict_db_names[_category].append(query.value("name"))
        query.finish()
        del query
        return dict_db_names
    
    def db_get_clades (self):
        """DBASE: Returns the list of distinct clades and groups from the taxa_wfo table"""
        #typically ['ANA Grade', 'Ceratophyllales', 'Chloranthales', 'Core Eudicots', 'Magnoliids', 'Monocots']
        sql_query = """
                    SELECT jsonb_object_agg(clade, idtaxonrefs)
                    FROM
                    (SELECT a.clade, 
                    array_agg(b.id_taxonref) AS idtaxonrefs 
                    FROM 
                    (	SELECT clade_apg AS clade, basename FROM taxonomy.taxa_wfo
                            WHERE clade_apg IS NOT NULL 
                        UNION 
                        SELECT major_plant_group, basename FROM taxonomy.taxa_wfo
                            WHERE major_plant_group IS NOT NULL 
                    ) a
                    INNER JOIN taxonomy.taxa_reference b ON a.basename = b.basename
                    GROUP BY a.clade)
                    """
                #execute the query
        query = self.db.exec(sql_query)
        json_list = [] #if no result, return empty json_list 
        if query.next():
            json_text = query.value(0)
            if json_text:
                json_list = json.loads(json_text)

        query.finish()
        del query
        return json_list



        if self.ls_taxa_groups:
            return self.ls_taxa_groups

        
        sql_query = """
                    SELECT clade
                    FROM
                        (SELECT clade_apg AS clade, 1 AS orderby FROM taxonomy.taxa_wfo
                            UNION
                         SELECT major_plant_group AS clade, 0 AS orderby FROM taxonomy.taxa_wfo
                        )
                    WHERE clade IS NOT NULL
                    ORDER BY orderby, clade;
                    """
        #execute the query
        query = self.db.exec(sql_query)
        json_list = []
        while query.next():
            json_list.append(query.value("clade"))
        query.finish()
        del query
        #save the list of distinct clades (re-use without querying database)
        self.ls_taxa_groups = json_list
        return json_list
    
    def db_get_taxa_wfo(self, filter_name = None):

        """DBASE: Returns a list of taxa-dictionary (dict_taxa) associated with wfo and potentially filtered by a taxaname (basename, group or clade))"""
        # the list of children from taxonomy.taxa_wfo, each item is a dictionary(id, taxaname, authors, rank, id_parent)
        table_taxa = []
        sql_where = ''
        if filter_name:
            filter_name = filter_name.strip().lower()
            sql_where = f"""WHERE '{filter_name}' IN (lower(basename), lower(major_plant_group), lower(clade_apg))"""
        sql_query = f"""
                        WITH RECURSIVE
                        wfo_indexing AS MATERIALIZED (
                            SELECT ROW_NUMBER() OVER (ORDER BY a.id_rank, a.basename ) AS id,
                            a.* 
                            FROM taxonomy.taxa_wfo a 
                        ),
                        wfo AS (
                            SELECT a.id, a.basename, a.id_rank, b.id AS id_parent, a.parent, a.authors, a.major_plant_group, a.clade_apg 
                            FROM wfo_indexing a 
                            LEFT JOIN wfo_indexing b
                            ON a.parent = b.basename
                        ),
                        anchor AS (
                            SELECT
                                c.id, c.id_parent, c.id_rank, c.basename, c.authors, c.parent
                            FROM wfo c
                            {sql_where}
                        ),
                        children AS (
                            SELECT * FROM anchor
                            UNION ALL
                            SELECT
                                c.id, c.id_parent, c.id_rank, c.basename, c.authors, c.parent
                            FROM wfo c
                            JOIN children p ON c.id_parent = p.id
                        ),
                        parents AS (
                            SELECT * FROM anchor
                            UNION ALL
                            SELECT
                                c.id, c.id_parent, c.id_rank, c.basename, c.authors, c.parent
                            FROM wfo c
                            JOIN parents p ON p.id_parent = c.id
                        ),
                        hierarchical AS (
                            SELECT * FROM children
                            UNION 
                            SELECT * FROM parents
                        )
                        SELECT a.id, a.id_parent, a.id_rank, a.basename, a.authors, a.parent, d.id_taxonref
                            FROM hierarchical a
                            LEFT JOIN taxonomy.taxa_reference d ON lower(a.basename) =  d.basename
                            ORDER BY a.id_rank;

                """
        #execute the query
        query = db().exec(sql_query)
        while query.next():
            item = {
                "id": query.value("id"),
                "id_parent": query.value("id_parent"),
                "id_rank" : query.value("id_rank"),
                "taxaname": query.value("basename").title(),
                "basename": query.value("basename"),
                "parentname": query.value("parent"),
                "authors": query.value("authors"),
                "rank": dbtaxa().db_get_rank(query.value("id_rank"), "rank_name"),
                "published" : True,
                "accepted" : True,
                "autonym" : False,
                "id_taxonref": query.value("id_taxonref")
            }
            table_taxa.append(item)
        return table_taxa

    def db_get_json_taxa(self, grouped_idrank, dict_filter = None) : #, refresh = False):
        """
            DBASE: Returns a list of taxa-dictionaries (dict_taxa) related to the dict_filter and grouped according to a rank
        """
            #ex: [{"id_taxonref":integer, "id_parent":integer, "id_rank" :integer, "taxaname":text, "authors":text, "published":boolean, "accepted":boolean, 
            #     "taxaname_score":numeric, "authors_score":numeric"}, ...]
        #refresh (inactif) -> only return childs of idtaxonref impacted by a name change (avoid refresh all childs of a rank but only those linked by name combination)
        _idrankspecies = self.db_get_rank('species', 'id_rank')
        #_idrankorder = self.db_get_rank('order', 'id_rank')
        #base_taxa = 'all_taxa'

        sql_where_taxa = ''
        tab_sql = [f"id_rank >= {_idrankspecies}"]
        sql_inner_join_taxa =''

        if dict_filter:
        #1) text filter: sql_where_taxa from the lineEdit_search
            txt_search = dict_filter.get("search_name", '')
            if txt_search:
                text_search = re.sub(r'[\*\%]', '', txt_search)
                #return a sql statement for searching taxanames
                sql_where_taxa = f"""\nc.id_taxonref IN (SELECT id_taxonref FROM taxonomy.pn_taxa_searchname ('%{text_search}%'))"""
                tab_sql.append(sql_where_taxa)
                
            #2) properties filter: sql_where_taxa from the PN_trview_filter (get the dict_user properties=
            tab_properties = dict_filter.get("properties", {})
            if tab_properties is None:
                tab_properties = {}
            for key, value in tab_properties.items():
                for key2, value2 in value.items():
                    if value2:
                        data = {key: {key2: value2}}
                        _prop = f"(properties @> '{json.dumps(data)}')"
                        tab_sql.append(_prop)
            #3) set the id_taxonref
            idtaxonref = dict_filter.get("id_taxonref", None)
            #idtaxonref = [16183, 17054, 16189]
            if idtaxonref:
                if not isinstance(idtaxonref, list):
                    idtaxonref = [idtaxonref]
                idtaxonref = ",".join(map(str, idtaxonref))
                sql_inner_join_taxa = f"""INNER JOIN 
                                        (SELECT id_taxonref FROM taxonomy.pn_taxa_hierarchy(ARRAY[{idtaxonref}])
                                        ) z ON s.id_taxonref = z.id_taxonref
                                       """
                                    
            # #4) APG Filter: add a filter for APG clade
            # clade_sql = dict_filter.get("clade", None)
            # if clade_sql:
            #     base_taxa = 'apg_taxa'
        
        # #5) create query: set the final sql_query, including sql_where_taxa and sql_join
        # sql_where_taxa = f" WHERE id_rank = {grouped_idrank} OR (" + " AND ".join(tab_sql) + ")"
        # sql_query = f"""
        # WITH 
        #     order_apg AS 
        #         (SELECT DISTINCT
        #             b.id_taxonref AS id_order,
        #             taxonomy.pn_taxa_getparent(b.id_taxonref, {grouped_idrank}) AS id_parent --to change
        #         FROM taxonomy.taxa_wfo a
        #         INNER JOIN taxonomy.taxa_reference b ON lower(a.basename) = b.basename
        #         WHERE b.id_rank = {_idrankorder} 
        #         AND a.major_plant_group = '{clade_sql}'
        #         OR a.clade_apg = '{clade_sql}'
        #         ),
        #     all_taxa AS            
        #         (SELECT a.id_taxonref, id_rank,
        #         	CASE WHEN id_rank >={_idrankspecies} THEN taxonomy.pn_taxa_getparent(a.id_taxonref, {grouped_idrank})
        #         	     ELSE id_parent
        #         	END
        #         	AS id_parent
        #             FROM taxonomy.taxa_reference a
        #             {sql_inner_join_taxa}
        #             {sql_where_taxa}
        #         ),
        #     apg_taxa AS
        #         (SELECT DISTINCT a.id_taxonref, a.id_parent, a.id_rank
        #             FROM all_taxa a
        #             LEFT JOIN order_apg b ON a.id_taxonref = b.id_parent
        #             LEFT JOIN order_apg c ON taxonomy.pn_taxa_getparent(a.id_taxonref, {_idrankorder}) = c.id_order
        #             WHERE c.id_order IS NOT NULL OR b.id_parent IS NOT NULL
        #         ),
        #     score_taxa AS 
        #         (SELECT 
        #             a.id_taxonref, b.id_parent, a.id_rank,
        #             a.taxaname, a.authors, a.published, a.accepted,
        #             (a.metadata->'score'->>'taxaname_score')::numeric AS taxaname_score,
        #             (a.metadata->'score'->>'authors_score')::numeric AS authors_score
        #             FROM {base_taxa} b
        #             INNER JOIN taxonomy.taxa_names a ON a.id_taxonref = b.id_taxonref
        #             ORDER BY taxaname
        #             )
        #     SELECT json_agg(row_to_json(score_taxa)) FROM score_taxa;
        # """

        sql_where_taxa = f" WHERE (" + " AND ".join(tab_sql) + ")"

        sql_query = f"""
        WITH 
        ranked AS 
            (SELECT a.id_taxonref, a.id_parent
            FROM taxonomy.taxa_reference a
            WHERE id_rank = {grouped_idrank}
            ),            
        children AS
            (SELECT b.id_taxonref, a.id_taxonref AS id_parent
            FROM ranked a,
            taxonomy.pn_taxa_childs(a.id_taxonref) b
            INNER JOIN taxonomy.taxa_reference c ON b.id_taxonref = c.id_taxonref
            
            {sql_where_taxa}
            ),
        all_taxa AS 
            (SELECT * FROM ranked
            UNION ALL
            SELECT * FROM children),
        score_taxa AS            
            (SELECT 
                s.id_taxonref,
                s.id_parent,
                n.id_rank,
                n.taxaname,
                n.authors,
                n.published,
                n.accepted,
                (n.metadata->'score'->>'taxaname_score')::numeric AS taxaname_score,
                (n.metadata->'score'->>'authors_score')::numeric AS authors_score
            FROM all_taxa s
            INNER JOIN taxonomy.taxa_names n ON n.id_taxonref = s.id_taxonref
            {sql_inner_join_taxa})

            
        SELECT json_agg(row_to_json(score_taxa)) FROM score_taxa;

        """


        #execute the query
        result = self.db.exec (sql_query)
        json_list = [] #if no result, return empty json_list 
        if result.next():
            json_text = result.value(0)
            if json_text:
                json_list = json.loads(json_text)

        result.finish()
        del result
        return json_list

#############################
    def db_get_taxon(self, id_taxonref):
        """DBASE: Return a taxa-dictionnary from id_taxonref"""
        sql_query = f"""
                    SELECT 
                        taxaname, authors, id_rank, published, accepted, id_parent 
                    FROM
                        taxonomy.taxa_names
                    WHERE
                        id_taxonref = {id_taxonref}
                   """
        #execute the query
        query = self.db.exec(sql_query)
        json_taxa = {}
        if query.next():
            json_taxa = {
                "id_taxonref": id_taxonref,
                "id_parent": query.value("id_parent"),
                "id_rank": query.value("id_rank"),
                "taxaname": query.value("taxaname"),
                "authors": query.value("authors"),
                "published": query.value("published"),
                "accepted": query.value("accepted")
            }
        query.finish()
        del query
        return json_taxa

#############################
    def db_get_list_hierarchy(self, id_taxonref):
        """DBASE: Returns a list of taxa-dictionary (dict_taxa) for a id_taxonref, ordered by rank, from Plantae to all children"""
        # Get the hierarchy for the selected taxa
        # try:
        #     if id_taxonref * id_rank == 0:
        #         return
        # except Exception:
        #     return
        # str_idtaxonref = str(id_taxonref)
        #sql_where = ''
        # extend to all taxa included in the genus when id_rank > genus (e.g. for species return all sibling species within the genus)
        #or in other words, set to the genus rank when id_rank > genus
        # if id_rank > 14: #get the genus rank at minimum
        #     str_idtaxonref = f"""(SELECT * FROM taxonomy.pn_taxa_getparent({str_idtaxonref},14))"""

        # sql_where = ''
        # create the SQL query to get the hierarchy of taxa
        _idrankgenus = self.db_get_rank('genus', 'id_rank')
        sql_query = f"""WITH get_idtaxonref AS 
                            (SELECT 
                                CASE WHEN
                                    id_rank >{_idrankgenus} THEN taxonomy.pn_taxa_getparent(id_taxonref, {_idrankgenus})
                                ELSE id_taxonref END
                                FROM taxonomy.taxa_reference tr 
                                WHERE id_taxonref = {id_taxonref}
                            )
        
                        SELECT 
                            b.id_taxonref, id_rank, id_parent, taxaname,  authors, published, accepted
                            FROM
                                (SELECT 
                                    id_taxonref
                                FROM    
                                    taxonomy.pn_taxa_parents((SELECT id_taxonref FROM get_idtaxonref), True)
                                UNION 
                                SELECT 
                                    id_taxonref
                                FROM 
                                    taxonomy.pn_taxa_childs((SELECT id_taxonref FROM get_idtaxonref), False)
                                ) a
                            INNER JOIN 
                                taxonomy.taxa_names b 
                            ON 
                                a.id_taxonref = b.id_taxonref
                        ORDER BY 
                            id_rank, taxaname;
                    """
        # execute the Query and fill the list_hierarchy of dictionnary
        query = self.db.exec(sql_query)
        #set the taxon to the hierarchical model rank = taxon
        ls_hierarchy = []
        while query.next():
            ls_hierarchy.append({
                "id_taxonref": query.value('id_taxonref'), 
                "id_parent": query.value('id_parent'), 
                "id_rank" : query.value('id_rank'), 
                "taxaname": query.value('taxaname').strip(), 
                "authors": query.value('authors').strip(), 
                "published": query.value('published'), 
                "accepted": query.value('accepted')
                }
            )
        query.finish()
        del query   
        return ls_hierarchy
    
    def db_get_properties (self, id_taxonref):
        """DBASE: Returns a json (dictionary of sub-dictionaries) from the field properties (jsonb) for an id_taxonref"""
        dict_db_properties = {}
        #create a copy of dict_properties with empty values
        db_properties = self.db_dic_properties
        for _key, _value in db_properties.items():
            dict_db_properties[_key] = {}.fromkeys(_value,'')
        #fill the properties from the json field properties annexed to the taxa        
        try:
            json_props = self.db_get_value("properties", id_taxonref)
            json_props = json.loads(json_props)
            for _key, _value in dict_db_properties.items():
                try:
                    tab_inbase = json_props[_key]
                    if tab_inbase is not None:
                        for _key2, _value2 in tab_inbase.items():
                            if _value2:
                                _value[_key2] = _value2.title()
                except Exception:
                    continue
        except Exception:
            pass
        return dict_db_properties

    def db_get_properties_count (self, id_taxonref):
        """DBASE: Returns a JSON aggregate (dictionary of subdictionaries) from the properties of the (jsonb) field of the children of id_taxonref"""
        #returns json only for taxa >= species
        _idrankspecies = self.db_get_rank('species', 'id_rank')
        sql_query = f"""
            WITH childs_taxaname AS 
                (
                    SELECT b.id_taxonref, b.properties 
                    FROM 
                    taxonomy.pn_taxa_childs({id_taxonref}) a
                    INNER JOIN taxonomy.taxa_reference b ON a.id_taxonref = b.id_taxonref
                    WHERE b.id_rank >={_idrankspecies}
                    AND b.properties IS NOT NULL 
                )
                SELECT jsonb_object_agg(key, fields) AS json_result
                FROM (
                    SELECT key, jsonb_object_agg(field, values_json) AS fields
                    FROM (
                        SELECT key, field, jsonb_object_agg(
                            replace(value::TEXT, chr(34), '')::TEXT, 
                            occurrence_count
                        ) AS values_json
                        FROM (
                            SELECT 
                                main.key AS key, 
                                sub.key AS field, 
                                sub.value::TEXT AS value, 
                                COUNT(*) AS occurrence_count
                            FROM childs_taxaname,
                            LATERAL jsonb_each(properties) AS main,
                            LATERAL jsonb_each(main.value) AS sub
                            GROUP BY main.key, sub.key, sub.value
                        ) grouped_data
                        GROUP BY key, field
                    ) fields_grouped
                    GROUP BY key
                ) final_json;
                    """
        #execute the query
        query = self.db.exec(sql_query)
        query.next()
        json_props = query.value("json_result")
        if json_props:
            json_props = json.loads(json_props)
        else:
            json_props = None
        query.finish()        
        del query
        return json_props
    
    def db_get_metadata (self, id_taxonref):
        """DBASE: Returns a json (dictionary of sub-dictionaries) from the field metadata (jsonb) for an id_taxonref"""
        #load metadata json from database
        json_data = self.db_get_value("metadata", id_taxonref)
        if not json_data:
            return None
        json_data = json.loads(json_data)
        #sorted the result, assure to set web links and query time ending the dict
        for key, metadata in json_data.items():
            _links = {'url':None, 'webpage':None} #, 'query time': None}
            if key.lower() =="score":
                _links = {}
            _fields = {}
            for _key, _value in metadata.items():
                if _key.lower() in _links:
                    _links[_key] = _value
                else:
                    _fields[_key] = _value
            #add the links to the fields
            #_fields = _fields | _links
            for _key, _value in _links.items():
                 if _value:
                    _fields[_key] = _value
            json_data[key] = _fields
        return json_data

    def db_delete_reference(self, id_taxonref):
        """DBASE: Deletes a reference and returns a list of deleted children (id_taxonrefs)"""
        ls_todelete = []
        #get the childs that will be deleted through foreign keys
        sql_query = f"SELECT id_taxonref FROM taxonomy.pn_taxa_childs ({id_taxonref}, True)"
        result = self.db.exec(sql_query)
        if not result.lastError().isValid():
            while result.next():
                ls_todelete.append(result.value("id_taxonref"))
        # delete the id_taxonref (and childs through integrity constraints)
        if ls_todelete:
            sql_query = f"SELECT taxonomy.pn_taxa_delete ({id_taxonref}) AS id_taxonref"
            result = self.db.exec(sql_query)
            if not result.lastError().isValid():
                return ls_todelete
        return []
    
    def db_save_dict_taxa(self, dict_tosave):
        """DBASE: Save a taxa-dictionary (dict_taxa) in the database, return id_taxonref (new or updated) or None if error"""
        #dict_tosave = {"id_taxonref":integer, "id_parent":integer, "id_rank" :integer, "basename":text, "authors":text, "parentname":text[None], "published":boolean, "accepted":boolean}
        return_idtaxonref = None
        idtaxonref = dict_tosave.get("id_taxonref", None)
        if idtaxonref is None:
            return None
        
        basename = dict_tosave.get("basename", None)
        if basename:
            basename = basename.strip().lower()
        else:
            return None
        #test for the types of update (according to specific fields parentname or id_parent)
        _parentname = dict_tosave.get("parentname", None)
        _idparent = dict_tosave.get("id_parent", None)
        published = dict_tosave.get("published", None)
        accepted = dict_tosave.get("accepted", None)
        authors = dict_tosave.get("authors", "").strip()
        authors = authors.replace("'", "''")  # escape single quotes
        idrank = dict_tosave.get("id_rank", None)

    #create the from_query depending if parentname/id_parent are present into the dictionnayr dict_tosave
    # if idtaxonref = 0 the function taxonomy.pn_taxa_edit will add a new taxonref, else edit the idtaxonref
        if _parentname:# get the id_parent from the parentname
            _parentname = _parentname.strip().lower() #.replace(' ', '')
            sql_update = f"""(SELECT 
                                taxonomy.pn_taxa_edit ({idtaxonref}, '{basename}', '{authors}', taxa.id_parent, {idrank}, {published}, {accepted}) AS id_taxonref 
                            FROM
                                (SELECT 
                                    a.id_taxonref AS id_parent
                                FROM
                                    taxonomy.taxa_nameset a
                                WHERE 
                                    lower(a.name) = '{_parentname}'
                                ) taxa
                            )
                        """
        elif _idparent:
            sql_update = f"""SELECT 
                                taxonomy.pn_taxa_edit ({idtaxonref}, '{basename}', '{authors}', {_idparent}, {idrank}, {published},{accepted}) AS id_taxonref"""
        else:
            return
        
    #1 - execute the sql_update and get the id_taxonref (update or add), if no error 
        sql_update = sql_update.replace("None", "NULL")
        #print (sql_update)
        result = self.db.exec (sql_update)
        #code_error = result.lastError().nativeErrorCode()

        #if no errors, return the id_taxonref
        # if result.lastError().isValid():
        #     msg = self.db().postgres_error()
        #     self.critical_msgbox ("Database error", msg)
        # el
        if result.next():
            return_idtaxonref = result.value("id_taxonref")    
        return return_idtaxonref
    

