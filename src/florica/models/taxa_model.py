# Standard library
import re
import time

# Third-party
import requests
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, QSortFilterProxyModel

# Internal
from florica.core import functions
from florica.core.widgets import load_ui_from_resources
from florica.models.api_taxonomy import API_Taxonomy

########################################
APIkey_tropicos = "afa96b37-3c48-4c1c-8bec-c844fb2b9c92"
########################################
def db_taxa():
    return functions.dbtaxa()

# Main classe to store a taxaname with some properties
class PNTaxa(object):
    """
    Main class to store a taxaname with associated properties and methods
    Fill data from database, if only id_taxonref is provided 
    Properties return values from database considering idtaxonref
    """
    def __init__(self, idtaxonref, taxaname = None, authors = None, idrank= None, published = None, accepted = None):
        self.id_taxonref = idtaxonref
        self.dict_species = None
        self.id_parent = None
        if taxaname:
            self.taxaname = taxaname
            self.authors = authors
            self.id_rank = idrank
            self.published = published
            self.accepted = accepted
        else:
            dict_taxa = db_taxa().db_get_taxon(self.id_taxonref)
            if dict_taxa is not None:
                self.taxaname = dict_taxa.get("taxaname", None)
                self.authors = dict_taxa.get("authors", None)
                self.id_rank = dict_taxa.get("id_rank", None)
                self.published = dict_taxa.get("published", None)
                self.accepted = dict_taxa.get("accepted", None)
                self.id_parent = dict_taxa.get("id_parent", None)


    def _part_name(self, fieldname):
        #create the dictionary of species parts if not yet done
        if self.dict_species is None:
            self.dict_species = functions.get_dict_from_species(self.taxonref)
        if self.dict_species is None:
            self.dict_species = {}
        #search and return the part (ex: basename, name, autonym, authors,...) from the dictionary
        if fieldname in self.dict_species:
            return self.dict_species[fieldname]
        else:
            return None
        

    @property
    def idtaxonref(self):
        """
        Returns the id_taxonref, 0 if errors
        """
        try:
            return int(self.id_taxonref)
        except Exception:
            return 0

    @property
    def rank_name (self):
        """
        Returns the name of the rank according to id_rank
        """
        try :
            txt_rk = db_taxa().db_get_rank(self.id_rank, 'rank_name')
        except Exception:
            txt_rk = 'Unknown'
        return txt_rk

    @property
    def id_rankparent (self):
        """
        Returns the id_rankparent (= the required parent rank) of a taxon based on id_rank
        """
        try :
            id_rp = db_taxa().db_get_rank(self.id_rank, 'id_rankparent')
        except Exception:
            id_rp = None
        return id_rp

    @property
    def taxonref(self):
        """
        Returns the taxonref (taxaname + authors) of a taxon
        """
        try :
            return " ".join([self.taxaname,self.authors]).strip()
        except Exception:
            return self.taxaname

    @property
    def isautonym (self):
        """
        Returns True if the taxa is an autonym for variety and subspecies
        """
        if self.id_rank not in [22,23]:
            return False
        return self._part_name ("autonym")

    @property
    def basename (self):
        """
        Returns the basic name of a taxon (not a compound one)
        """
        if self.id_rank < 21:
            return self.taxaname.lower()
        return self._part_name ("basename")

    @property
    def simple_taxaname (self):
        """
        Returns the simple taxaname of a taxon (with no authors if infraspecies)
        """
        if self.id_rank < 21:
            return self.taxaname
        return self._part_name ("name")
    
    @property
    def json_names(self):
        """     
        Returns a json (dictionary) of all names grouped by category
        """
        return db_taxa().db_get_names(self.idtaxonref)

    @property 
    def json_metadata (self):
        """     
        Returns a json (dictionary of sub-dictionaries) for metadata(jsonb)
        """              
        return db_taxa().db_get_metadata(self.idtaxonref)
    
    @property
    def json_properties_count(self):
        """     
        Returns a json (dictionary of sub-dictionaries) of the count of taxa properties(jsonb) from child taxa
        """        
        return db_taxa().db_get_properties_count(self.idtaxonref)

    @property
    def json_properties(self):
        """     
        Returns a json (dictionary of sub-dictionaries) for properties(jsonb)
        """
        return db_taxa().db_get_properties(self.idtaxonref)

    @property
    def list_hierarchy(self):
        """     
        Returns a list of taxa-dictionary ordered from Plantae to children
        """
        return db_taxa().db_get_list_hierarchy(self.idtaxonref)

    @property
    def valid_parents(self):
        """
        Returns a dictionary of valid parents of the taxon for moving
        """
        return db_taxa().db_get_valid_parents(self.idtaxonref)

    @property
    def valid_merges(self):
        """
        Returns a dictionary of valid sibling of the taxon for merging
        """
        return db_taxa().db_get_valid_merges(self.idtaxonref)

#class to represent taxa with scoring information
class PNTaxa_with_Score(PNTaxa):
    """Subclass of PNTaxa with additional properties for scoring."""
    def __init__(self, idtaxonref, taxaname = None, authors = None, idrank= None, published = None, accepted = None):
        super().__init__(idtaxonref, taxaname, authors, idrank, published, accepted)
        self.taxaname_score = None
        self.authors_score = None
        self.visible = True

    @property
    def taxaname_percent(self):
        """Returns the taxaname score in percentage"""
        try:
            return str(round(100 * self.taxaname_score, 1)) + "%"
        except Exception:
            return None
        
    @property
    def authors_percent(self):
        """Returns the authors score in percentage"""
        try:
            return str(round(100 * self.authors_score, 1)) + "%"
        except Exception:
            return None

class PN_TaxaSearch(QtWidgets.QWidget):
    """
    The PN_TaxaSearch class is a custom class that inherits from QtWidgets.QWidget.
    It is designed to display a search widget composed of a search text and a Qtreeview result with matched taxa and score.

    Attributes:
        lineEdit_search_taxa (QtWidgets.QLineEdit): The search text input field.
        treeview_scoretaxa (QtWidgets.QTreeView): The treeview widget that displays the search results.

    Methods:
        __init__ : Initializes the search widget.
        setText : Sets the text of the search input field.
        selectedTaxa : Returns the selected taxon object.
        selectedTaxonRef : Returns the reference of the selected taxon.
        selectedScore : Returns the score of the selected taxon.
        selectedTaxaId : Returns the ID of the selected taxon.

    Signals:
        selectionChanged (str): Emitted when the selection in the treeview changes.
        doubleClicked (object): Emitted when an item in the treeview is double-clicked.

    """
    selectionChanged = pyqtSignal(str)
    doubleClicked = pyqtSignal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        # load the GUI
        self.lineEdit_search_taxa = QtWidgets.QLineEdit(self)
        self.treeview_scoretaxa = QtWidgets.QTreeView(self)
        self.lineEdit_search_taxa.setPlaceholderText("search taxa")
        self.treeview_scoretaxa.setEditTriggers(QtWidgets.QTreeView.NoEditTriggers)
        #set the model
        self.model = QtGui.QStandardItemModel()
        self.model.setColumnCount(2)
        self.treeview_scoretaxa.setModel(self.model)
        self.treeview_scoretaxa.setHeaderHidden(True)
        #connect slots
        self.treeview_scoretaxa.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.treeview_scoretaxa.doubleClicked.connect(self.on_doubleClicked)
        self.lineEdit_search_taxa.textChanged.connect(self.on_text_changed)
        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.lineEdit_search_taxa)
        layout.addWidget(self.treeview_scoretaxa)
        self.setLayout(layout)
    
    def setText(self, newtext):
        self.lineEdit_search_taxa.setText(newtext)

    def currentIndex(self):
        return self.treeview_scoretaxa.currentIndex()
    
    def selectedTaxa(self):
        return self.treeview_scoretaxa.currentIndex().siblingAtColumn(0).data()
    
    def selectedTaxonRef(self):
        parent = self.treeview_scoretaxa.currentIndex().parent()
        if parent.isValid():
            return parent.data()
        else:
            return self.treeview_scoretaxa.currentIndex().data()
        
    def selectedTaxaId(self):
        parent = self.treeview_scoretaxa.currentIndex().parent()
        if parent.isValid():
            return parent.data(Qt.UserRole)
        else:
            return self.treeview_scoretaxa.currentIndex().data(Qt.UserRole)
    
    def selectedScore(self):
        return self.treeview_scoretaxa.currentIndex().siblingAtColumn(1).data()
    
    def on_selection_changed(self, selected):
        index = selected.indexes()[0] if selected.indexes() else None
        if index:
            selected_item = index.data()
            self.selectionChanged.emit(selected_item)  # Emit the slot selected_item
            
    def on_doubleClicked(self, index):
        self.doubleClicked.emit(index)  # Emit the slot selected_item

    def on_text_changed(self):
        #"main" function to search for taxa resolution
        self.model.clear()
        search_txt = self.lineEdit_search_taxa.text()
        #get the list of search names with score
        ls_searchnames = db_taxa().db_get_fuzzynames(search_txt, 0.4)
        if ls_searchnames is None:
            return
        #set the item into the model
        for name, item in ls_searchnames.items():
            id_taxonref = item['id_taxonref']
            ref_item = [QtGui.QStandardItem(name), QtGui.QStandardItem(item['score'])]
            ref_item[0].setData(id_taxonref, Qt.UserRole)
            ref_item[1].setTextAlignment(Qt.AlignCenter)
            self.model.appendRow(ref_item)
            #set score in red if below 50
            if item['score'] < 50:
                _color =  QtGui.QColor(255, 0, 0)
                ref_item[1].setData(QtGui.QBrush(_color), Qt.ForegroundRole)
            for synonym in item['synonym']:
                ref_item[0].appendRow ([QtGui.QStandardItem(synonym)])
                
        if self.model.rowCount() > 0:
            self.treeview_scoretaxa.resizeColumnToContents(1)
            self.treeview_scoretaxa.setExpanded(self.model.index(0, 0), True)
            self.treeview_scoretaxa.header().setStretchLastSection(False)
            self.treeview_scoretaxa.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
            self.treeview_scoretaxa.header().setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)

#class to search taxa through API
class PNTaxa_searchAPI (QtCore.QThread):
    """
    Worker thread to query multiple biodiversity APIs asynchronously.

    Emits:
        Result_Signal (str, object): Signal emitted with API name and data dictionary
            or special status strings like "END" or "NOTCONNECTED".
    Args:
        parent (QObject): Parent QObject for the thread.
        myPNTaxa (object, optional): Model or taxon object to query. Defaults to None.
        filter (str, optional): Limits queries to a single API from the supported list. Defaults to None.
    Attributes:
        PNTaxa_model (object): The taxon model to query.
        status (int): Thread status flag, 1 for running, 0 for stopped.
        list_api (list): List of API names to query.
    """
    
    Result_Signal = pyqtSignal(str, object)
    
    def __init__(self, parent, myPNTaxa = None, filter = None):
        """
        Initialize the thread with taxon model and optional API filter.
        """
        QtCore.QThread.__init__(self, parent)
        self.PNTaxa_model = myPNTaxa
        self.api_Taxonomy = API_Taxonomy()
        self.list_api = list(self.api_Taxonomy.api_classes.keys())
        self.status = 0
        #apikey_tropicos = "afa96b37-3c48-4c1c-8bec-c844fb2b9c92"
        #self.list_api =  ["POWO","TAXREF","IPNI","TROPICOS","ENDEMIA","FLORICAL", "INATURALIST", "GBIF"]
        # test for a _filter (= one of the valid base (IPNI, POWO, TAXREF, TROPICOS))
        try:
            if filter in self.list_api:
                self.list_api = [filter]
        except Exception:
            pass
        
    def kill(self):
        """
        Signal to stop the thread's operation and emit an "END" signal.
        """
        try:
            self.Result_Signal.emit("END", None)
        finally :
            self.status = 0

    def run(self):
        """
        Main thread loop that queries each API in the list sequentially.

        Steps:
            - Checks for internet connectivity.
            - Iterates over the APIs to query metadata and synonyms.
            - Emits results through Result_Signal.
            - Stops if status is set to 0.
        """        
        _list_api = {}
        
        #test for a effective connection
        try:
            requests.get("https://www.google.com", timeout=2)
        except Exception:
            self.Result_Signal.emit("NOTCONNECTED", None)
            return
        
        if self.PNTaxa_model is None:
            self.Result_Signal.emit("END", None)
            return
        #set the variables
        _name = self.PNTaxa_model.simple_taxaname
        _rank = self.PNTaxa_model.rank_name
        #_key_tropicos = "afa96b37-3c48-4c1c-8bec-c844fb2b9c92"
        #self.list_api = ["GBIF"]

        #add only classes accepted id_rank for searching
        list_api_tosearch = []
        for key, value in self.api_Taxonomy.api_classes.items():
            _children = value.get("search", 0)
            if self.PNTaxa_model.id_rank >= _children:
                list_api_tosearch.append(key)
        #set variables for scoring
        self.status = 1
        total_checked = 0
        total_fullname = 0
        total_authors  = 0
        total_match = 0
        _score = {"authors_score": 0, "taxaname_score": 0, "query_time": time.strftime("%Y-%m-%d %H:%M:%S")}

        for api_name in list_api_tosearch:
            _json = None
            #check for status
            if self.status == 0: 
                return
            #set the key (if tropicos)
            _key = None
            if api_name == "TROPICOS":
                _key = APIkey_tropicos
            #search the taxon in the API            
            result = self.api_Taxonomy.get_APIclass(api_name, _name, _rank, _key)
            if not result.API_url:
                continue
            if result.API_error:
                if result.API_error.startswith("Connection error"):
                    continue
            total_checked += 1

            if result is None :
                continue
        #get the metadata
            _json = result.get_metadata()
            #delete None values
            if _json:
                if "query time" in _json:
                    del _json["query time"] #delete query time for each json, use a common query_time in _score dictionary
                _json = {k: v for k, v in _json.items() if v is not None}
            
            #add synonyms if exists and emit intermediate signal
            if _json:
                total_match +=1
                t_synonyms = result.get_synonyms()
                if t_synonyms:
                    _json["synonyms"] = t_synonyms

            #check if the author name is the same considering only alphanumeric characters
                if _json.get ("authors", None):
                    total_authors += 1
                    _json_authors = re.sub(r'[^A-Za-z]', '', _json["authors"]).lower()
                    _pn_authors = re.sub(r'[^A-Za-z]', '', self.PNTaxa_model.authors).lower()
                    if _json_authors == _pn_authors:
                        total_fullname += 1                    
                self.status += 1
                _list_api[api_name] = _json
            #create intermediate _json (score and _json error will not be included in the _list_api final !)
            if not _json:
                _json = {"error": "No results", "url":result.API_url}
            _json = _json.copy()
            #create score dictionary
            _score["taxaname_score"] = total_match / total_checked if total_checked > 0 else 0
            _score["authors_score"] = total_fullname / total_authors if total_authors > 0 else 0
            #emit intermediate signal
            _json["score"] = _score
            self.Result_Signal.emit(str(api_name), _json)

            
            if self.status == 0 : 
                return
            time.sleep(0.2)
        #emit final signal
        #create score dictionary
        _score["taxaname_score"] = total_match / total_checked if total_checked > 0 else 0
        _score["authors_score"] = total_fullname / total_authors if total_authors > 0 else 0
        _list_api["score"] = _score
        self.Result_Signal.emit("END", _list_api)

            


    # @property 
    # def total_api_calls(self):
    #     return (self.status-1)
    

#class to display a treeview with hiercharchical taxonomy
class PNTaxa_QTreeView(QtWidgets.QTreeView):
    """
    The PNTaxa_QTreeView class is a custom class that inherits from QtWidgets.QTreeView.
    It is designed to display a hierarchical taxonomic structure.
    The class takes a PNTaxa object as input to define the taxonomic hierarchy.
    """
    def __init__(self):
        """Initializes the tree view window, disabling editing capabilities."""
        super().__init__()
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        model = QtGui.QStandardItemModel()
        self.setModel(model)
        self.ls_hierarchy = None
    
    def setdata(self, myPNTaxa, currentIdtaxonref = None):
        """Populates the treeview with the taxonomic hierarchy based on a PNTaxa object"""
        #It creates a SQL query to retrieve the hierarchy, executes the query, and populates the tree view with the results."""
        # Get the hierarchy for the selected taxa
        model = self.model()
        model.clear()
        self.ls_hierarchy = None
        
        self.ls_hierarchy = myPNTaxa.list_hierarchy
        if not self.ls_hierarchy:
            return
        
        ls_pn_taxa = []
        for item in self.ls_hierarchy:
            id_taxonref = item['id_taxonref']
            idrank = item['id_rank']
            taxaname = item['taxaname'].strip()
            authors = item['authors'].strip()
            published = item['published']
            accepted = item['accepted']
            idparent = item['id_parent']
            #print (db_taxa().db_get_rank(idrank, "rank_name"))
            pn_item = PNTaxa_with_Score(id_taxonref, taxaname, authors, idrank, published, accepted)
            pn_item.id_parent = idparent
            ls_pn_taxa.append(pn_item)


        dict_idtaxonref = {}
        for item in ls_pn_taxa:
            _itemrank = item.rank_name
            if not item.published and item.id_rank >=3:
                _itemrank += " (ined.)"
            dict_idtaxonref[item.idtaxonref] = [QtGui.QStandardItem(_itemrank), QtGui.QStandardItem(item.taxonref)]

        for item in ls_pn_taxa:
            #search for a parent_item in the dictionary of item index on id_taxonref
            item_parent = dict_idtaxonref.get(item.id_parent, None)
            item_taxon = dict_idtaxonref.get(item.idtaxonref, None)
            #append as child or root
            if item_parent:
                item_parent[0].appendRow(item_taxon)
            else:
                # append as a new line if item not found (or first item)
                model.appendRow(item_taxon)
            #if item_rank:
            item_taxon[0].setData(item, Qt.UserRole)
            # set italic if not published
            if not item.published:
                font = QtGui.QFont()
                font.setItalic(True)
                model.setData(item_taxon[0].index(), font, Qt.FontRole)
            if not item.accepted:
                model.setData(item_taxon[0].index(), QtGui.QColor(255, 0, 0), Qt.ForegroundRole)

        #get the selection
        current_item = None
        #item_selected = self.currentIndex().siblingAtColumn(0).data(Qt.UserRole)
        if currentIdtaxonref is not None:
            current_item = dict_idtaxonref.get(currentIdtaxonref, None)

        if current_item is None:
            current_item = dict_idtaxonref.get(myPNTaxa.idtaxonref, None)         

        # set bold the current id_taxonref line (2 first cells) and italized authors if not published
            
        key_index = None
        if current_item:
            # font = QtGui.QFont()
            # font.setBold(True)
            key_index = current_item[0].index()
        if key_index:
            #select and ensure visible the key_index (automatic scroll)
            self.selectionModel().setCurrentIndex(key_index, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)
            self.scrollTo(key_index,QtWidgets.QAbstractItemView.PositionAtCenter)  # PositionAtTop/EnsureVisible
            
        self.setHeaderHidden(True)
        self.setColumnWidth(0, 300)
        self.expandAll()

    def selecteditem(self) -> "PNTaxa":
        """
        Returns the selected PNTaxa from the hierarchical model
        """
        try:
            return self.currentIndex().siblingAtColumn(0).data(Qt.UserRole)
        except:
            return None





#proxy class linked to PNTaxa_add (= proxymodel)
class _CheckableOnlyProxy(QSortFilterProxyModel):
    """Internal class to filter only checkable items as a proxy model"""
    def __init__(self):
        super().__init__()
        self.only_checkable = False   # ← OFF par défaut

    def setOnlyCheckable(self, enabled: bool):
        self.only_checkable = enabled
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        # desactivated filter (all rows)
        if not self.only_checkable:
            return True
        model = self.sourceModel()
        index = model.index(row, 0, parent)
        if not index.isValid():
            return False
        # visible if checkable
        if model.flags(index) & Qt.ItemIsUserCheckable:
            return True
        # visible if at least one child is checkable
        for i in range(model.rowCount(index)):
            if self.filterAcceptsRow(i, index):
                return True
        return False
  


#class to add a taxon
class PNTaxa_add(QtWidgets.QMainWindow):
    """
        Class representing a window for adding taxonomic data to a PNTaxa object, using user-entered data, a WFO list, or API data.
        Returns a dictionary of taxa (dict_tosave) when the user clicks the Apply button.
        Attributes:
        myPNTaxa (PNTaxa): An instance of the `PNTaxa` class that provides access to the taxonomic data.        
        Signals:
        apply_signal: A signal that is emitted when the user clicks the Apply button.
    """
    apply_signal  = pyqtSignal(object)
    def __init__(self, myPNTaxa):
        """Initialize the class with the given `myPNTaxa`."""
        super().__init__()
        self.PNTaxa = myPNTaxa
        self.table_taxa = []
        #self._taxaname = ''
        #self.updated = False
        #self.prefix = ''
        #self.id_rank = None

        #set the ui
        self.window = load_ui_from_resources("pn_addtaxa.ui")
        self.window.trView_childs.setVisible(False)
        self.window.combo_group.setVisible(False)
        self.window.checkBox_filter_new.setVisible(False)
        self.window.taxaLineEdit_result.setText('')

        #set buttons icons        
        button_apply = self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply)
        button_close = self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Close)        
        button_apply.setIcon (QtGui.QIcon(":src/florica/resources/icons/ok.png"))
        button_close.setIcon (QtGui.QIcon(":src/florica/resources/icons/nok.png"))
        button_apply.setEnabled(False)

        #set the model to the treeview_childs
        model = QtGui.QStandardItemModel()
        self.proxy = _CheckableOnlyProxy()
        self.proxy.setSourceModel(model)
        self.window.trView_childs.setModel(self.proxy)
        self.window.trView_childs.setColumnWidth(0,250)

        #manage the combo_group
        self.window.combo_group.addItem("All names")
        self.window.combo_group.addItem(myPNTaxa.taxaname)
        lst = db_taxa().db_get_clades()
        for clade in lst:
            self.window.combo_group.addItem(clade)
        self.window.combo_group.setCurrentIndex(1)

        #Manage the taxonomy_api class
        self.taxonomy_api = API_Taxonomy()
        #_idrank = self.PNTaxa.id_rank
        api_class_toadd = {}
        #add Tab only for API classes with a get_children function
        if self.PNTaxa.id_rank <10:
            self.window.tabWidget_main.addTab(QtWidgets.QWidget(), 'WFO')       
        for key, value in self.taxonomy_api.api_classes.items():
            _children = value.get("children", None)
            if _children and self.PNTaxa.id_rank >=_children:
                api_class_toadd[key] = value     
        for api_class in api_class_toadd.keys():
            self.window.tabWidget_main.addTab(QtWidgets.QWidget(), api_class.title())

        #manage slot and signals
        button_apply.clicked.connect(self._on_button_apply_clicked)
        button_close.clicked.connect (self._on_button_close_clicked)
        self.window.tabWidget_main.currentChanged.connect(self._on_tabWidget_click)
        self.window.combo_group.activated.connect(self._on_combo_group_clicked)
        self.window.checkBox_filter_new.toggled.connect(self._on_checkbox_filter_toggled)
        self.window.basenameLineEdit.textChanged.connect (self._validate)
        self.window.authorsLineEdit.textChanged.connect (self._validate)
        self.window.rankComboBox.activated.connect(self._validate)
        self.window.checkBox_published.toggled.connect(self._validate)
        self.window.checkBox_accepted.toggled.connect(self._validate)

        #load rankcombo_box
        rank_childs = db_taxa().db_get_rank(self.PNTaxa.id_rank, "childs") 
        for idrank in rank_childs:
            rank_name = db_taxa().db_get_rank(idrank, 'rank_name')
            self.window.rankComboBox.addItem(rank_name, idrank)


        self._validate()

    def _validate(self):
        """Evaluate the new name and authors combination, then enable/disable the Apply button"""
        self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(False)
        self.window.taxaLineEdit_result.setText('')

        #check for a valid newbasename
        newbasename = self.window.basenameLineEdit.text().strip().title()
        newbasename = newbasename.replace(' ', '')
        if len(newbasename) < 3:
            return
        
        #get authors & published
        newauthors = self.window.authorsLineEdit.text()
        parentname = self.PNTaxa.taxaname
        published = self.window.checkBox_published.isChecked()
        id_rank = self.window.rankComboBox.itemData(self.window.rankComboBox.currentIndex())
        ined = None
        taxa = None
        prefix = None
        if not newauthors or not published:
            ined = '(ined.)'

        #add prefix if species or infraspecies
        if id_rank >=21:
            newbasename = newbasename.lower()
            prefix = db_taxa().db_get_rank(id_rank, 'prefix') or ''
        #set the taxa name
        taxa = " ".join(str(part) for part in [parentname, prefix, newbasename, newauthors, ined] if part)
        self.window.taxaLineEdit_result.setText(taxa)
        #set the apply status
        _apply = id_rank < 14 or len(newbasename) >= 3
        self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(_apply)
  
    def _has_checked_item(self):
        """Returns True if a least one item is checked"""
        for taxa in self.table_taxa:
            if taxa["item"].checkState() == 2:
                return True
        return False

    def _unchecked_child(self, item):
        """Unchecked item and childrens, with a recursive function"""
        for row in range(0, item.rowCount()):
            item2 = item.child(row,0)
            if item2.isCheckable():
                item2.setCheckState(0)
            if item2.hasChildren():
                self._unchecked_child(item2)
        return
    
    def _checked_parent(self, item):
        """Checked item and parents, with a recursive function"""
        try:
            item_parent = item.parent()
            if item_parent.isCheckable():
                item_parent.setCheckState(2)
                self._checked_parent(item_parent)
        except Exception:
            return
        
    def _checked_children(self, item):
        """Checked item and childrens, with a recursive function"""
        for row in range(item.rowCount()):
            child = item.child(row)
            if child and child.isCheckable():
                child.setCheckState(2)
                self._checked_children(child)

    def _checked_taxa(self, id=0):
        """Return a list of taxa checked into table_taxa with a recursive function"""
        if id == 0:
            id = self.table_taxa[0]["id"]
        tab_result=[]
        for taxa in self.table_taxa:
            if taxa["id_parent"] == id and taxa.get("item", None):
                item = taxa["item"]
                if item.checkState()==2:
                    #taxa["parent"] = taxaname
                    tab_result.append(taxa)
                tab_result += self._checked_taxa(taxa["id"])
        return tab_result

    def _draw_table_taxa(self):
        """Draw the hierarchical tree according to idparent and id in the list of taxa-dictionaries (self.table_taxa)"""
        if self.window.tabWidget_main.currentIndex() == 0:
            return
        #model = self.window.trView_childs.model()
        model = self.proxy.sourceModel()
        model.setRowCount(0)
        self.checkable = 0
        #disconnect the itemChanged signal
        self._connect_signal_trview_childs(False)
        
        def draw_list_recursive(taxon, parent_item=None):
            #internal recursive function to build hierarchical tree according to idparent and id
            taxaref = f'{taxon["taxaname"]} {taxon.get("authors", "")}'.strip()
            _checkable = (taxon["id_taxonref"] == 0 and not taxon.get ("autonym", False))
            item = QtGui.QStandardItem(str(taxon["rank"]))
            item1 = QtGui.QStandardItem(taxaref.strip())       
            item.setCheckable(False)
            item.setData(None, Qt.CheckStateRole)
            item.setCheckable(_checkable)
            taxon["item"] = item
            if _checkable:
                self.checkable += 1
            #add node to the model
            if parent_item is None:
                model.appendRow([item, item1])
            else:
                parent_item.appendRow([item, item1])
            for child in taxon["children"]:
                draw_list_recursive(child, item)

        #browse the table_taxa to build a tree structure
         #first create a dictionary of parent
        dict_parent = {item["id"]: item for item in self.table_taxa}
        roots = []
        for taxa in self.table_taxa:
            taxa["children"]= []
            node_parent = dict_parent.get(taxa["id_parent"], None)
            if node_parent is None:
                roots.append(taxa)
            else:
                node_parent["children"].append(taxa)
        #add each root node to the model by recursive function
        for root in roots:
            draw_list_recursive(root)

        self.window.trView_childs.expandAll()
        #self.window.trView_childs.expandToDepth(1)
            
        #add message to the label
        index = self.window.tabWidget_main.currentIndex()
        _api_name = self.window.tabWidget_main.tabText(index).title()
        self.window.checkBox_filter_new.setVisible(False)
        if self.checkable > 0:
            self.window.checkBox_filter_new.setVisible(True)
            self.window.label_2.setText("Check taxa to add (Ctrl to add children)")
        else:
            self.window.label_2.setText("No new taxa to add from " + _api_name)
        #reconnect the itemChanged signal
        self._connect_signal_trview_childs(True)

    def _connect_signal_trview_childs(self, connect = False):
        """Connect/Disconnect the checked signal event itemChanged to trview_childs"""
        model = self.proxy.sourceModel()
        #disconnect the itemChanged signal
        try:
            model.itemChanged.disconnect()
        except Exception:
            pass        
        #connect if true
        if connect:
            model.itemChanged.connect(self._on_trview_checked_click)

    def _on_trview_checked_click(self, checked_item):
        """Checked/Unchecked item with parent, and childs according to keyboard"""
        state = checked_item.checkState()
        _apply = False
        ctrl_pressed = QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier
        
        #disconnect the itemChanged signal
        self._connect_signal_trview_childs(connect = False)

        if state == 2 :
            self._checked_parent(checked_item)
            _apply = True
            if ctrl_pressed:
                self._checked_children(checked_item)
        elif state == 0:
            self._unchecked_child(checked_item)
            _apply = self._has_checked_item()
        #set the state of the apply button
        self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(_apply)
        self._connect_signal_trview_childs(connect = True)

    def _on_combo_group_clicked (self):
        """Refresh the current category"""
        index = self.window.tabWidget_main.currentIndex()
        self._on_tabWidget_click(index)
        
    def _on_checkbox_filter_toggled (self, value):
        self.proxy.setOnlyCheckable(value)
        self.window.trView_childs.expandAll()
        self.window.trView_childs.resizeColumnToContents(0)
        self.window.trView_childs.resizeColumnToContents(1)

    def _on_tabWidget_click(self, index = None):
        """Click on a tabWidget_main item"""
        if index is None:
            index = self.window.tabWidget_main.currentIndex()
    #change tabWidget_main item (user search or internet search)
        self.window.trView_childs.setVisible(False)
        self.window.combo_group.setVisible(False)
        self.window.checkBox_filter_new.setVisible(False)
    #index = 0 --> USER
        if index == 0 : 
            self.window.label_2.setText("Add taxon")
            self.window.taxaLineEdit_result.setVisible(True)
            self._validate()
            return
    #else --> WFO or API
        _apibase = self.window.tabWidget_main.tabText(index)
        self.window.taxaLineEdit_result.setVisible(False)
        self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(False)
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(Qt.WaitCursor))
        #get data (list of dictionary) from API class function get_children"
        # a list of childs elements
        #exemple {"id" : '10', "taxaname" : 'Genus species', "authors" : 'Not me', "rank" : 'Species', "idparent" : '1'}
        # note that the id_parent of each taxa except the first one must be in the list, if not it will excluded
        #self.window.frame_filter.setVisible(True)
        self.window.combo_group.setVisible (False)
    #add the widgets to the layout
        layout = self.window.tabWidget_main.currentWidget().layout()
        if layout is None:
            layout = QtWidgets.QGridLayout()
            self.window.tabWidget_main.currentWidget().setLayout(layout)
        #add the widget to the layout
        layout.addWidget(self.window.combo_group)
        layout.addWidget(self.window.trView_childs)
        self.window.trView_childs.setVisible(True)

    #draw the list in the tree view
        self.window.label_2.setText("Searching into " + _apibase + "...")
        model = self.proxy.sourceModel()
        model.setRowCount(0)
        model.setColumnCount(2)
        QtWidgets.QApplication.processEvents()
        msg = "Null Value"
        _apibase = _apibase.upper()
        self.table_taxa = []        
        if _apibase == "WFO": #add taxa from the internal datalist (WFO)
            self.window.combo_group.setVisible(True)
            #_filter the taxasearch with a keyword (None or from combo_clade)
            _filter = None
            if self.window.combo_group.currentIndex() > 0:
                _filter = self.window.combo_group.currentText()
            #get the list of dictionaries (cf. db_get_taxa_wfo)
            self.table_taxa = db_taxa().db_get_taxa_wfo (_filter)
        else: #use self.taxonomy_api            
            _name = self.PNTaxa.simple_taxaname
            _rank = self.PNTaxa.rank_name
            #set the key (if tropicos)
            _key = None
            if _apibase == "TROPICOS":
                _key = APIkey_tropicos
            #get the class and errors
            result = self.taxonomy_api.get_APIclass(_apibase, _name, _rank, _key)
            msg = self.taxonomy_api._api_class.API_error
            #get children
            if result:
                #result.getchildren is a list of dictionary ex: [{"id" : '10', "taxaname" : 'Genus species', "authors" : 'Not me', "rank" : 'Species', "idparent" : '1'}] 
                self.table_taxa = result.get_children()
            if self.table_taxa:
                #add mandatories fields for display and save
                #search for existing taxaname in the dbase (return a dictionary id_taxonref by taxaname for existing taxaname)
                names = [d["taxaname"].strip() for d in self.table_taxa]     
                dict_id_taxonref = db_taxa().db_get_searchnames(names)
                #add an index dictionary to search for taxaname from id_taxonref
                dict_parent = {item["id"]: item["taxaname"] for item in self.table_taxa}
                #ajust the dictionary, add special fields
                for taxa in self.table_taxa:                
                    _tabtaxa = taxa["taxaname"].split()
                    taxa["id_taxonref"] = dict_id_taxonref.get(taxa["taxaname"], 0)
                    taxa["parentname"] = dict_parent.get(taxa["id_parent"], "")
                    taxa["basename"] = _tabtaxa[-1]
                    taxa["authors"] = functions.get_str_value(taxa["authors"])
                    taxa["id_rank"] = db_taxa().db_get_rank(taxa["rank"], "id_rank")
                    taxa["published"] = len (taxa["authors"]) > 0
                    taxa["accepted"] = True
                    taxa["autonym"] = False
                    if taxa["id_rank"] > 21 and len(_tabtaxa) >= 4:
                        taxa["autonym"] = (_tabtaxa[1] == taxa["basename"])

        #check existing taxa and draw the treeview model
        if self.table_taxa:
            self._draw_table_taxa ()
            self.window.trView_childs.sortByColumn(1, Qt.AscendingOrder)
        #set an item msg if not found
        if model.rowCount() ==0:
            msg = msg or f"{self.PNTaxa.taxaname} is not found"
            model.appendRow([QtGui.QStandardItem("< No data > "), QtGui.QStandardItem(msg)],)
            self.proxy.setOnlyCheckable(False)
        #ajust columns

        self.window.trView_childs.resizeColumnToContents(0)
        self.window.trView_childs.resizeColumnToContents(1)
        #self.window.trView_childs.expandToDepth(1)
        while QtWidgets.QApplication.overrideCursor() is not None:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _on_button_apply_clicked(self):
        """Valid the form and emit signal (apply_signal) with a taxa-dictionary (dict_tosave)."""
    #apply add taxa
        #self.updated = False        
        index = self.window.tabWidget_main.currentIndex()
    #for user table
        if index == 0 :
            newbasename = self.window.basenameLineEdit.text().strip()            
            newpublished = self.window.checkBox_published.isChecked()
            newaccepted = self.window.checkBox_accepted.isChecked()
            newauthors = self.window.authorsLineEdit.text().strip()
            newidparent = self.PNTaxa.idtaxonref
            #newidrank = self.data_rank[self.window.rankComboBox.currentIndex()]
            newidrank = self.window.rankComboBox.itemData(self.window.rankComboBox.currentIndex())
            #create the pn_taxa_edit query function (internal to postgres)
            if len(newauthors) == 0:
                newpublished = False
            dict_tosave = {"id_taxonref":0, "basename":newbasename, "authors":newauthors, "id_parent":newidparent, "published":newpublished, "accepted":newaccepted, "id_rank":newidrank}
            self.apply_signal.emit(dict_tosave)
            return

    #for API tabs
        #get the dict_tosave for each checked taxa to add
        taxa_toAdd = self._checked_taxa()
        if taxa_toAdd is None:
            return
        if len(taxa_toAdd) == 0:
            return
        #emit the signal to save the taxa
        self.apply_signal.emit(taxa_toAdd)
        return

    def _on_button_close_clicked(self):
        """Close the add window."""
        self.window.close()

    def refresh (self):
        """Refresh the content of the add window."""
        self.window.basenameLineEdit.setText('')
        self.window.authorsLineEdit.setText('')
        self.window.checkBox_published.setChecked(False)
        self.window.checkBox_accepted.setChecked(False)
        self._draw_table_taxa()

    def show(self):
        """Show the add window."""
        self.window.show()
        self.window.exec_()


    # def on_rankCombo_change(self):
    #     self.id_rank = self.window.rankComboBox.itemData(self.window.rankComboBox.currentIndex())
    #     self.prefix = db_taxa().db_get_rank(self.id_rank, 'prefix')
    #     self._validate()

    # def rankComboBox_setdata(self):
    #     rank_childs = db_taxa().db_get_rank(self.PNTaxa.id_rank, "childs") 
    #     index = -1
    #     for idrank in rank_childs:
    #         rank_name = db_taxa().db_get_rank(idrank, 'rank_name')
    #         self.window.rankComboBox.addItem(rank_name, idrank)
    #         #self.data_rank.append(idrank)
    #         if idrank == self.PNTaxa.id_rank:
    #             index = self.window.rankComboBox.count()-1
    #     index = max(index, 0)
    #     try:
    #         self.window.rankComboBox.setCurrentIndex(index)
    #     except Exception:
    #         return        

#edit a taxa and apply by emit signal 
class PNTaxa_edit(QtWidgets.QMainWindow):
    """
        Class providing a user interface for editing taxonomic data (PNTaxa).
        Returns a dictionary of taxa (dict_tosave) when the user clicks the Apply button.
        Attributes:
        MyPNTaxa (PNTaxa): An instance of the `PNTaxa` class that provides access to the taxonomic data.
        Signals:
        apply_signal: A signal that is emitted when the user clicks the Apply button.
    """       
    apply_signal  = pyqtSignal(object)
    def __init__(self, myPNTaxa):
        """Init the class PNTaxa_edit and UI"""
        super().__init__()
        self.PNTaxa = myPNTaxa
        #set the ui 
        self.window = load_ui_from_resources("pn_edittaxa.ui")

        #force the style to reflect green/red checkbox
        _style = """
            QCheckBox::indicator:checked {
                background-color: rgb(0, 255, 0);
                border: 1px solid darkgreen;
            }
            QCheckBox::indicator:unchecked {
                background-color: rgb(255, 0, 0);
                border: 1px solid darkred;
            }
            QCheckBox::indicator:indeterminate {
                background-color: white;
                border: 1px solid #555;
            }
        """
        self.window.checkBox_published.setStyleSheet(_style)
        self.window.checkBox_accepted.setStyleSheet(_style)

        #load the list of parents in the parent_comboBox
        ls_valid_parents = self.PNTaxa.valid_parents
        for key, value in ls_valid_parents.items():
            self.window.parent_comboBox.addItem (key, value)
     
        #connect the signal to the slot
        self.window.basenameLineEdit.textChanged.connect (self._validate)
        self.window.authorsLineEdit.textChanged.connect (self._validate)
        self.window.checkBox_published.toggled.connect(self._validate)
        self.window.checkBox_accepted.toggled.connect(self._validate)
        self.window.parent_comboBox.activated.connect(self._validate)

        # define buttons icons and signal
        button_apply = self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply)
        button_close = self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Close)

        button_apply.setIcon (QtGui.QIcon(":src/florica/resources/icons/ok.png"))
        button_close.setIcon (QtGui.QIcon(":src/florica/resources/icons/nok.png"))

        button_apply.setEnabled(False)
        button_apply.clicked.connect(self._on_button_apply_clicked)
        button_close.clicked.connect(self._on_button_close_clicked)

        #load the contents from the PNTaxa object
        self.refresh()

        #self.comboBox_parent_setdata()
        # self.window.basenameLineEdit.setText(self.PNTaxa.basename)
        # self.window.authorsLineEdit.setText(self.PNTaxa.authors)
        # self.window.checkBox_published.setChecked(self.PNTaxa.published)
        # self.window.checkBox_accepted.setChecked(self.PNTaxa.accepted)
        # self._validate()
        #self.input_name = self.window.taxaLineEdit.text()

    def _validate(self):
        """Validate the new combination of name and authors, and set the apply button enabled or disabled."""
        parentname = None
        prefix = None
        ined = ''        
        taxa =''
        newbasename = self.window.basenameLineEdit.text().title().strip()
        newauthors = self.window.authorsLineEdit.text()
        published = (self.window.checkBox_published.isChecked())
        accepted = (self.window.checkBox_accepted.isChecked())
        #create the temporary taxonref
        if not newauthors or not published:
            ined = 'ined.'
        # elif not published:
        #     ined = 'ined.'
        try:
            if self.PNTaxa.id_rank >=21:
                parentname = self.window.parent_comboBox.currentText()
                prefix = db_taxa().db_get_rank(self.PNTaxa.id_rank, 'prefix')
                newbasename = newbasename.lower()
            taxa = " ".join(str(part) for part in [parentname, prefix, newbasename, newauthors, ined] if part)
        except Exception:
            taxa = " ".join([newbasename, newauthors, ined])
        #set the title of the window
        self.window.taxaLineEdit.setText(taxa)

        #if text is different than input text than activated apply button
        if len(self.PNTaxa.basename) == 0 : 
            return
        _idparent = self.window.parent_comboBox.itemData(self.window.parent_comboBox.currentIndex(), Qt.UserRole)
        _apply = (
                (self.PNTaxa.basename != newbasename.lower()) or
                (self.PNTaxa.authors != newauthors) or
                (self.PNTaxa.id_parent != _idparent) or
                (self.PNTaxa.published != published) or 
                (self.PNTaxa.accepted != accepted)
                )   
        self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).setEnabled(_apply)

    def _on_button_close_clicked(self):
        """close the window"""
        self.window.close()

    def _on_button_apply_clicked(self):
        """Emit a signal with a taxa-dictionnary (dict_tosave)"""
        self.updated = False 
        idtaxonref = self.PNTaxa.idtaxonref
        newbasename = self.window.basenameLineEdit.text().strip()
        published = (self.window.checkBox_published.isChecked())
        accepted = (self.window.checkBox_accepted.isChecked())
        newauthors = self.window.authorsLineEdit.text().strip()
        newidparent = self.window.parent_comboBox.itemData(self.window.parent_comboBox.currentIndex(), Qt.UserRole)
        #create and return the taxa-dictionnary (dict_tosave) through the apply_signal
        dict_tosave = {"id_taxonref":idtaxonref, "basename":newbasename, "authors":newauthors, "id_parent":newidparent, "published":published, "accepted":accepted, "id_rank" :self.PNTaxa.id_rank}
        self.apply_signal.emit(dict_tosave)
        return True

    def refresh (self):
        """Refresh UI with PNTaxa"""
        self.window.basenameLineEdit.setText(self.PNTaxa.basename)
        self.window.authorsLineEdit.setText(self.PNTaxa.authors)
        self.window.checkBox_published.setChecked(self.PNTaxa.published)
        self.window.checkBox_accepted.setChecked(self.PNTaxa.accepted)
        index = self.window.parent_comboBox.findData(self.PNTaxa.id_parent)
        self.window.parent_comboBox.setCurrentIndex(index)
        self._validate()

    def show(self):
        """Show the edit window."""
        self.window.show()
        self.window.exec_()

    # def comboBox_parent_setdata(self):
    #     #fill the combo box with valid parents for the current taxon
    #     self.window.parent_comboBox.clear()
    #     ls_valid_parents = self.PNTaxa.valid_parents
    #     index = -1
    #     for key, value in ls_valid_parents.items():
    #         self.window.parent_comboBox.addItem (key, value)
    #     #     if value == self.PNTaxa.id_parent:
    #     #         index = self.window.parent_comboBox.count()-1
    #     # self.window.parent_comboBox.setCurrentIndex(index)




#merge two taxa and create synonyms
class PNTaxa_merge(QtWidgets.QMainWindow):
    def __init__(self, myPNTaxa): # move toward a same id_rank if merge
        super().__init__()
        self.PNTaxa = myPNTaxa
        self.updated = False
        #set the ui
        self.window = load_ui_from_resources("pn_movetaxa.ui")
        self.window.setMaximumHeight(1)
        
        self.window.comboBox_category.addItems(['Homotypic', 'Heterotypic'])
        self.window.comboBox_category.setCurrentIndex(0)
        self.window.comboBox_category.activated.connect(self.set_newtaxanames)
        
        self.window.comboBox_taxa.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.window.comboBox_taxa.activated.connect(self.set_newtaxanames)
        #button_OK = self.window.buttonBox

        button_apply = self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply)
        button_close = self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Close)        
        button_apply.setIcon (QtGui.QIcon(":src/florica/resources/icons/ok.png"))
        button_close.setIcon (QtGui.QIcon(":src/florica/resources/icons/nok.png"))

        button_apply.clicked.connect (self.accept) 
        button_close.clicked.connect (self.close)
        
        self.window.taxaLineEdit.setText(self.PNTaxa.taxonref)
        self.comboBox_taxa_setdata()
    @property
    def selected_idtaxonref(self):
        index = self.window.comboBox_taxa.currentIndex()
        return self.window.comboBox_taxa.itemData(index)
    @property
    def selected_category(self):
        return self.window.comboBox_category.currentText()
    
    def set_newtaxanames(self):
    #Display the new names and return the sql query
        # set the resulting label (synonym expression)
        category_synonym = chr(8801)
        if self.window.comboBox_category.currentIndex() > 0:
            category_synonym = chr(61)
        txt_taxa = self.PNTaxa.taxonref +  ' ' + category_synonym + ' ' +self.window.comboBox_taxa.currentText()
        self.window.label_result.setText(txt_taxa)
        return


    def comboBox_taxa_setdata(self):
        #fill the combo box with valid sibling to merge for the current taxon
        self.window.comboBox_taxa.clear()
        ls_valid_sibling = self.PNTaxa.valid_merges #db_taxa().db_get_valid_merges(self.PNTaxa.idtaxonref)
        index = -1
        for key, value in ls_valid_sibling.items():
            self.window.comboBox_taxa.addItem (key, value)
            if value == self.PNTaxa.idtaxonref:
                index = self.window.comboBox_taxa.count()-1
        self.window.comboBox_taxa.setCurrentIndex(index)
               
    def accept(self):
    #Valid the form, save the data into the dbase and return
    #a list of PNTaxa that have been updated
        if self.PNTaxa.idtaxonref == self.selected_idtaxonref:
            return
        self.updated = True
        self.close()
    
    
    def close(self):
        self.window.close()
 
    def show(self):
        self.window.show()
        self.window.exec_()

#classes (PNTaxa_treeModel containing PNTaxa_treeItem) to create an abstract model to display taxon with parent
class PNTaxa_treeItem:
    """
    This class represents a tree item in the PNTaxa_treeModel abstract data model.
    It is used to store information about a taxon and its parent-child relationship.
    """
    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []
    
    @property
    def childCount(self) -> int:
        """Return the number of child tree items."""
        return len(self.childItems)
    
    def parent(self) -> "PNTaxa_treeItem":
        """Return the parent of the item"""
        return self.parentItem

    def row(self) -> int:
        """Return the row number of the item"""
        if self.parentItem is None:
            return 0
        return self.parentItem.childItems.index(self)

    def appendChild(self, item):
        """Add a child to the Item"""
        self.childItems.append(item)

    def child(self, row):
        """Return the child at the specified row."""
        return self.childItems[row]
####################

class PNTaxa_treeModel(QtCore.QAbstractItemModel):
    """
    This class represents a data model for displaying a hierarchical structure of taxa.
    It inherits from `QtCore.QAbstractItemModel` and is designed to display taxa with their parents.
    """
    
    header_labels = ['Name', 'Authors']
    refresh_signal = pyqtSignal()

    def __init__(self, data=None, parent=None):
        super(PNTaxa_treeModel, self).__init__(parent)
        self.rootItem = PNTaxa_treeItem(None)
        self.parent_nodes = {}
        self.sort_column = 0
        self.sort_order = QtCore.Qt.AscendingOrder
        self.items = data if data else []
        # self.show_nodes_with_children_only = 0 #2 = root nodes with children only (no others options)
        # self.show_nodes_published = 1  #0=all, 1=published only, 2=unpublished only
        # self.show_nodes_accepted = 1  #0=all, 1=accepted only, 2=unaccepted only
        # self.show_nodes_checked = 1
        # self.filter_published = None
        # self.filter_accepted = None
        #option to show or not orphelin taxa (not referenced into the grouped node)
        #self.show_orphelins = True
        #self.items = set(data) if data else set()
        #self._setupModelData()


    def _getNode(self, idtaxonref):
        """Return the node (TreeItem) corresponding to the idtaxonref"""
        return self.parent_nodes.get(idtaxonref, None)

    def _setupModelData(self, item = None):
        """Create the model from the list of items (self.items), set the parent and the children"""
        if item:
            items = [item]
        else:
            items = self.items
        
        # first loop, create a dictionary for every items
        dict_parent = {item.idtaxonref: item.id_parent for item in self.items}

        # second loop to detect parents node(id_parent is None)
        for item in items:
            node_parent = dict_parent.get(item.id_parent, None)
            if node_parent is None:
                # If no parent is found, create a new root item
                #if self._getNode(item.idtaxonref) is None:
                self.parent_nodes[item.idtaxonref] = PNTaxa_treeItem(item, self.rootItem)
                self.rootItem.appendChild(self.parent_nodes[item.idtaxonref])

        # third loop to create the children of the respective parent
        for item in items:
            #only add childs where id_rank >=21
            if getattr(item, 'id_rank', 0) < 21:
                continue
            idparent = getattr(item, 'id_parent', 0)
            if idparent in self.parent_nodes:
                childItem = PNTaxa_treeItem(item, self.parent_nodes[idparent])
                self.parent_nodes[item.idtaxonref] = childItem
                self.parent_nodes[idparent].appendChild(childItem)
        #emit signal to inform the model has been refreshed
        self.refresh_signal.emit()

    def _create_multi_score_icon(self, scores, radius=8, spacing=3, shape='ellipse'):
        """
            Creates a QIcon with several elements side by side (ellipses or rectangles), automatically sized according to the number of scores.
            scores : list of scores
            radius : size of each element
            spacing : spece between each icons
            shape : 'ellipse' or 'rect'
        """
        n = len(scores)
        width = n * radius + (n - 1) * spacing
        height = radius + 2
        px = QtGui.QPixmap(width, height)
        px.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(px)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        for i, score in enumerate(scores):
            colour = self._getcolour(score)
            x = i * (radius + spacing)
            painter.setBrush(colour)
            if shape == 'ellipse':
                painter.drawEllipse(QtCore.QRect(x, 1, radius, radius))
            elif shape == 'rect':
                painter.drawRect(QtCore.QRect(x, 1, radius, radius))

        painter.end()
        return QtGui.QIcon(px)
    
    def _getcolour(self, score):
        """Return the color corresponding to the score (black (None), red (0), green (1), yellow (else))"""
        if score is None:
            return QtGui.QColor(0, 0, 0)
        else:
            return {0: QtGui.QColor(255, 0, 0), 1: QtGui.QColor(0, 255, 0)}.get(score, QtGui.QColor(255, 255, 0))




    def indexItem(self, idtaxonref, column=0):
        """Return the index of the item corresponding to the idtaxonref"""
        tree_item = self._getNode (idtaxonref)
        if tree_item is None or tree_item == self.rootItem:
            return QtCore.QModelIndex()

        parent_item = tree_item.parent()
        if parent_item is None:
            return QtCore.QModelIndex()

        row = parent_item.childItems.index(tree_item)
        return self.createIndex(row, column, tree_item)

    def getItem(self, idtaxonref)-> PNTaxa:
        """Return the item (PNTaxa) corresponding to the idtaxonref"""
        TreeItem = self._getNode(idtaxonref)
        return TreeItem.itemData if TreeItem else None
    
    def removeItem(self, id_taxonref):
        """Remove the item and childs (PNTaxa) corresponding to the idtaxonref"""
        def delete_all_children(node):
            # Remove the PNTaxa_with_score from the items list
            if node.itemData in self.items:
                self.items.remove(node.itemData)
            # Remove from the parent_nodes dictionary
            taxon_id = getattr(node.itemData, 'id_taxonref', None)
            if taxon_id in self.parent_nodes:
                del self.parent_nodes[taxon_id]
            for child in node.childItems:
                # recursive call on children
                delete_all_children(child)

        #get the TreeItem from the idtaxonref
        item = self._getNode(id_taxonref)
        if not item:
            return
        #get the parent of the TreeItem
        parent = item.parent()
        if not parent:
            return
        #set the QmodelIndex for the parent
        try:
            parent_index = self.createIndex(parent.row(), 0, parent) if parent != self.rootItem else QtCore.QModelIndex()
        except Exception:
            return
        row = item.row()
        #delete the item and childs from the parent list
        self.beginRemoveRows(parent_index, row, row)
        #delete all children recursively
        delete_all_children(item)
        #delete the node itself
        if item in parent.childItems:
            parent.childItems.remove(item)
        self.endRemoveRows()


    def clear(self):
        """Clear the model, reset the items list"""
        #clear the model
        self.beginResetModel()
        self.rootItem = PNTaxa_treeItem(None)
        self.parent_nodes = {}
        self.items = []
        self.endResetModel()

    def refreshData(self, new_PNTaxa_items = None):
        """Refresh the entire model, replacing items with the new items if provided"""
        #save the items before clear
        if not new_PNTaxa_items:
            new_PNTaxa_items = self.items
        # else:
        self.clear()
        #set the items list
        self.items = new_PNTaxa_items

        #reset the model and setup the new data
        self.beginResetModel()
        # self.rootItem = PNTaxa_treeItem(None)
        # self.parent_nodes = {}
        self._setupModelData()
        self.endResetModel()

    def columnCount(self, parent=QtCore.QModelIndex()):
        """Return the number of columns in the model."""
        return 2

    def rowCount(self, parent=QtCore.QModelIndex()):
        """Return the number of rows in the model."""
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
        return parentItem.childCount

    def index(self, row, column, parent=QtCore.QModelIndex()):
        """Return the index of the item at the given row and column."""
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        return QtCore.QModelIndex()

    def parent(self, index):
        """Return the parent of the item at the given index."""
        if not index.isValid():
            return QtCore.QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem or parentItem is None:
            return QtCore.QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)


    def data(self, index, role=Qt.DisplayRole):
        """
            Set the data for each item in the model according to the role
        """
        if not index.isValid():
            return None
        item = index.internalPointer()
        col = index.column()

        if item.itemData is None:
            return None
        _published = getattr(item.itemData, 'published', False)
        _accepted = getattr(item.itemData, 'accepted', False)
        
        if role == Qt.UserRole:
            return item.itemData
        elif role == Qt.FontRole:
            if not _published:
                font = QtGui.QFont()
                font.setItalic(True)
                return font
        elif col == 0 :
            if role == Qt.DisplayRole:
                return item.itemData.taxaname
            elif role == Qt.DecorationRole:
                return self._create_multi_score_icon([
                        item.itemData.taxaname_score,
                        item.itemData.authors_score
                    ], shape='ellipse')
            elif role == Qt.TextAlignmentRole:
                if hasattr(item.itemData, 'id_rank') and item.itemData.id_rank >= 21:
                    return Qt.AlignRight | Qt.AlignVCenter
                else:
                    return Qt.AlignLeft | Qt.AlignVCenter
            elif role == Qt.ToolTipRole:
                
                parts = []
                # Explanation of the taxaname score
                parts.append(f"Taxaname: {item.itemData.taxaname_percent}")
                parts.append(f"Authors: {item.itemData.authors_percent}")
                # Explanation of the publication status
                parts.append(f"Published: {_published}")
                parts.append(f"Accepted: {_accepted}")
                return "\n".join(parts)
        elif col == 1:
            if role == Qt.DisplayRole:
                if item.itemData.isautonym:
                    return "[Autonym]"
                text = item.itemData.authors or ""
                if not _published:
                    text += " (ined.)"
                return text.strip()
            elif role == Qt.DecorationRole:
                return self._create_multi_score_icon([
                    int(_published),
                    int(_accepted)
                ], shape='rect')
        

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set the header labels from self.header_labels"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header_labels[section]
        return None



    # def taxa_count(self):
    #     """Return the total number of taxa (child items) in the model"""
    #     return sum(item.childCount() for item in self.parent_nodes.values())


    # def sortItems(self, column, order=Qt.AscendingOrder, rootItem=None):
    #     """Sorting the model items by a column (by default all the model)"""
    #     def recursive_sort(item):
    #         item.childItems.sort(
    #             key=lambda i: i.data(column).lower() if isinstance(i.data(column), str) else i.data(column),
    #             reverse=(order == Qt.DescendingOrder)
    #         )
    #         for child in item.childItems:
    #             recursive_sort(child)
    #     if not rootItem:
    #         rootItem = self.rootItem
    #     self.sort_column = column
    #     self.sort_order = order
    #     recursive_sort(rootItem)
    #     self.layoutChanged.emit()

    # def addItem(self, myPNTaxa):
    # #add a new item to the model, NOT PERSISTENT IN DATABASE
    # #add only id_rank >=21 with a node parent existing
    #     #if myPNTaxa.id_rank < 21 or 
    #     if self.getItem(myPNTaxa.id_parent) is None:
    #         return
    #     self.items.append(myPNTaxa)
    #     self._setupModelData(myPNTaxa)



    # def refresh (self, myPNTaxas = None):
    #     #Refresh the content of the model, NOT PERSISTENT IN DATABASE
    #     ##By default refresh the entire model (myPNTaxa = None)
    #     #look for refresh id_taxonref if exists otherwise append the new row
    #     #refresh the entire model if myPNTaxa is None
    #     if myPNTaxas is None:
    #         self.refreshData()
    #         return
    #     #ensure the myPNTaxas is a list
    #     if not isinstance(myPNTaxas, list):
    #         ls_myPNTaxas = [myPNTaxas]
    #     else:
    #         ls_myPNTaxas = myPNTaxas
    #     #browse the list and refresh or add the items
    #     node_parent = None
    #     self.beginResetModel()
    #     # self.rootItem = PNTaxa_treeItem(None)
    #     # self.parent_nodes = {}
    #     for myPNTaxa in ls_myPNTaxas:
    #         node_parent = self._getNode(myPNTaxa.id_parent)
    #         node_item = self._getNode(myPNTaxa.idtaxonref)
    #         if node_item: #item already exists
    #             #do not move root items
    #             if node_item.parentItem is not self.rootItem:
    #                 #delete if node_parent is NULL
    #                 if node_parent is None:
    #                     self.removeItem(myPNTaxa.idtaxonref)
    #                     continue
    #                 #if parent different, move the node to the new parent
    #                 elif node_item.parentItem != node_parent:
    #                     #delete the item from the old parent
    #                     if node_item in node_item.parentItem.childItems:
    #                         node_item.parentItem.childItems.remove(node_item)
    #                     #set the new parent
    #                     node_item.parentItem = node_parent
    #                     node_parent.appendChild (node_item)
    #             #swap the existing itemData with the new one in self.items and node_item
    #             item = node_item.itemData
    #             i = self.items.index(item)
    #             self.items[i] = myPNTaxa
    #             #finally change the itemData of the node_item
    #             node_item.itemData = myPNTaxa
    #         else: #if node_parent: #new item on an existingn parent
    #             # self.beginInsertRows(
    #             #     self.createIndex(node_parent.row(), 0, node_parent),
    #             #     node_parent.childCount(),
    #             #     node_parent.childCount()
    #             # )
    #             print ("add :", myPNTaxa.taxaname)
    #             self.items.append(myPNTaxa)
    #             #self.endInsertRows()
    #             #sort the model
    #             #self.sortItems(self.sort_column, self.sort_order, node_parent)
    #     self._setupModelData()
    #     self.endResetModel()

####################
#class to reference a synonym
class PNSynonym(object):
    def __init__(self, synonym = None, taxonref = None, idtaxonref = 0, category = 'Orthographic'):
        self.synonym = synonym
        self.category = category
        self.taxon_ref = taxonref
        self.id_taxonref = idtaxonref

    @property
    def idtaxonref(self):
        """Returns an integer value of id_taxonref, 0 if errors"""
        try:
            return int(self.id_taxonref)
        except Exception:
            return 0

    @property
    def resolved(self):
        """Returns True if idtaxonref>0""" 
        return self.idtaxonref > 0  
    

####################
# Class to edit(New or update) synonym
class PNSynonym_edit (QtWidgets.QWidget):
    """
    Class providing a user interface for editing/adding a synonym (PNSynonym)
    If not resolved (idtaxonref = 0), user can search for a idtaxonref (PN_TaxaSearch)
    Emit signal (edit or add) when the user clicks the Apply button
    """
# add/update a new synonym to a idtaxonref or search for a idtaxonref (PN_TaxaSearch) according to a synonym 
    #button_click = pyqtSignal(object, int)
    add_signal  = pyqtSignal(int, str, str)
    edit_signal  = pyqtSignal(str, str, str)

    def __init__(self, myPNSynonym):
        super().__init__()
        self.treeview_searchtaxa = None
        self.myPNSynonym = myPNSynonym
        self.is_new = (self.myPNSynonym.synonym is None or self.myPNSynonym.idtaxonref == 0)
        
        #set the ui
        self.window = load_ui_from_resources("pn_editname.ui")
        self.Qline_name = self.window.name_linedit
        self.Qline_ref = self.window.taxaLineEdit
        self.Qcombobox = self.window.comboBox
        self.Qline_name.setReadOnly(not self.myPNSynonym.resolved)
        self.Qline_name.setText('') 
        self.window.setMaximumHeight(500)
        self.window.resize(500,500)

        # self.Qcombobox.setCurrentText(str(self.myPNSynonym.category))
        # self.Qline_name.setText(self.myPNSynonym.synonym)
        #resolved depends if idtaxonref is Null
        if not self.myPNSynonym.resolved:
            self.treeview_searchtaxa = PN_TaxaSearch()
            self.window.label_tip.setText('Select Reference...')
            #add the treeview_searchtaxa = Class PN_TaxaSearch() (cf. taxa_model.py)
            layout = self.window.QTreeViewSearch_layout
            layout.addWidget(self.treeview_searchtaxa)
            self.treeview_searchtaxa.setText(self.myPNSynonym.synonym)
            self.treeview_searchtaxa.selectionChanged.connect(self._validate)
        else: #idtaxonref is not Null
            if self.is_new:
                self.window.label_tip.setText('New Synonym...')
            else:
                self.window.label_tip.setText('Edit Synonym...')
            self.Qline_ref.setText(self.myPNSynonym.taxon_ref)
            self.window.setMaximumHeight(1)
            self.Qline_name.setFocus()
        #self._validate()
        
        #manage buttons icons
        self.button_apply = self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Apply)
        button_close = self.window.buttonBox.button(QtWidgets.QDialogButtonBox.Close)
        self.button_apply.setIcon (QtGui.QIcon(":src/florica/resources/icons/ok.png"))
        button_close.setIcon (QtGui.QIcon(":src/florica/resources/icons/nok.png"))

        #set the signals
        self.Qline_name.textChanged.connect (self._validate)
        self.Qcombobox.activated.connect(self._validate)
        self.button_apply.clicked.connect (self._on_button_apply_clicked)
        button_close.clicked.connect (self._on_button_close_clicked)

        self.refresh()


    def _validate(self):
        """Evaluate the new name and category combination, then enable/disable the Apply button."""
        txt_item = self.Qline_name.text().strip()
        txt_category = self.Qcombobox.currentText().strip()         
        flag = False
        if len(txt_item)>=3:
            if self.myPNSynonym.resolved:
                flag = not (self.myPNSynonym.synonym == txt_item and self.myPNSynonym.category == txt_category)
            else:
                new_taxonref = self.treeview_searchtaxa.selectedTaxonRef()
                flag = new_taxonref is not None
                self.Qline_ref.setText(new_taxonref)
        self.button_apply.setEnabled(flag)
        
    def _on_button_close_clicked(self):
        """Close the edit/add window."""
        self.window.close()

    def _on_button_apply_clicked(self):
        """Valid the form, and emit signal (add_signal/edit_signal) with values."""
        #self.updated = False
        new_synonym = self.Qline_name.text().strip()
        new_category = self.Qcombobox.currentText().strip()
        if self.is_new:
            #add mode
            self.add_signal.emit(self.myPNSynonym.idtaxonref, new_synonym, new_category)
        else:
            #edit mode
            self.edit_signal.emit(self.myPNSynonym.synonym, new_synonym, new_category)

    def show(self):
        """Show the edit window."""
        self.window.show()
        self.window.exec()

    def refresh(self):
        """Refresh UI with PNSynonym."""
        self.Qcombobox.setCurrentText(str(self.myPNSynonym.category))
        self.Qline_name.setText(self.myPNSynonym.synonym)
        self._validate()
