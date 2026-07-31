import requests
import urllib3
import json
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WFO_URL = "https://list.worldfloraonline.org/gql.php"




import json

def introspect_type(type_name, depth=0, visited=None):

    if visited is None:
        visited = set()

    if type_name in visited:
        print("  " * depth + f"{type_name} (already visited)")
        return

    visited.add(type_name)

    query = """
    query ($typeName: String!) {
      __type(name: $typeName) {
        name
        kind

        fields {
          name
          type {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }

        enumValues {
          name
        }
      }
    }
    """

    result = gql(query, {"typeName": type_name})
    t = result["data"]["__type"]

    if not t:
        print("  " * depth + f"{type_name} (NOT FOUND)")
        return

    indent = "  " * depth

    print(f"\n{indent}{t['name']} [{t['kind']}]")

    # -------------------------
    # ENUM
    # -------------------------
    if t["kind"] == "ENUM":
        for v in t.get("enumValues", []):
            print(f"{indent}  - {v['name']}")
        return

    # -------------------------
    # OBJECT
    # -------------------------
    for field in t.get("fields", []):
        f_name = field["name"]
        f_type = field["type"]

        kind = f_type["kind"]
        name = f_type.get("name")

        # -------------------------
        # SCALAR
        # -------------------------
        if kind == "SCALAR":
            print(f"{indent}- {f_name}: {name}")

        # -------------------------
        # ENUM
        # -------------------------
        elif kind == "ENUM":
            print(f"{indent}- {f_name}: ENUM<{name}>")
            introspect_type(name, depth + 2, visited)

        # -------------------------
        # OBJECT
        # -------------------------
        elif kind == "OBJECT":
            print(f"{indent}- {f_name}: {name}")
            introspect_type(name, depth + 2, visited)

        # -------------------------
        # LIST
        # -------------------------
        elif kind == "LIST":
            of = f_type.get("ofType")

            if of and of.get("name"):
                inner_name = of["name"]

                print(f"{indent}- {f_name}: [{inner_name}]")

                if of["kind"] != "SCALAR":
                    introspect_type(inner_name, depth + 2, visited)

            else:
                print(f"{indent}- {f_name}: [unknown]")









def gql(query, variables=None):
    try:
      r = requests.post(
          WFO_URL,
          json={"query": query, "variables": variables or {}},
          verify=False
      )
      return r.json()
    except Exception as e:
      return None
    #return(json.dumps(r.json(), indent=2, ensure_ascii=False))

  





def get_metadata(name_id: str):
    if name_id is None:
        return None
    query = """
    query ($id: String!) {
      taxonNameById(nameId: $id) {
        id
        fullNameStringPlain
        fullNameStringHtml
        authorsString
        rank
        nomenclaturalStatus
        comment

      references {
        uri
        label
        comment
        kind
        thumbnailUri
      }

        
        currentPreferredUsage {
          id
          title
          stableUri
          pathString
        }
        identifiersOther {
    kind
    value
}


      }
    }
    """

    data = gql(query, {"id": name_id})

    return data["data"]["taxonNameById"]









def resolve_taxon_metadata(name):

    query = """
    query ($input: String!) {
      taxonNameMatch(inputString: $input) {
        error
        match {
          id
          fullNameStringNoAuthorsPlain
          authorsString
          rank
          nomenclaturalStatus
          comment

          currentPreferredUsage {
            # id
            # title
            stableUri        
          hasSynonym {
          #id
          #nameString
          #fullNameStringPlain
          fullNameStringNoAuthorsPlain
          authorsString
        }  
          }
        
        }


        # candidates {
        #   id
        #   fullNameStringPlain
        #   authorsString
        # }
      }
    }
    """
    res = gql(query, {"input": name})["data"]["taxonNameMatch"]
    if res["error"]:
        return None
    dict_final = {"id":None, "name": None, "authors":None, "status": None, "rank": None, "comment": None, "publication": None, "synonyms": None, "webpage":None}
    if res["match"]:
        taxa = res["match"]
        dict_final["id"] = taxa["id"]
        dict_final["name"] = taxa["fullNameStringNoAuthorsPlain"]
        dict_final["authors"] = taxa["authorsString"]
        dict_final["status"] = taxa["nomenclaturalStatus"]
        dict_final["rank"] = taxa["rank"]
        dict_final["comment"] = taxa["comment"]
        dict_final["webpage"] = taxa["currentPreferredUsage"]["stableUri"]

        #taxa["url"] = taxa["currentPreferredUsage"]["stableUri"]
        ls_synonyms = []
        dict_syno = taxa["currentPreferredUsage"]["hasSynonym"]
        if dict_syno:
            for syno in dict_syno:
                ls_synonyms.append(syno["fullNameStringNoAuthorsPlain"])
                ls_synonyms.append(syno["fullNameStringNoAuthorsPlain"]+ ' ' + syno["authorsString"])
            dict_final["synonyms"] = ls_synonyms
        #del taxa["currentPreferredUsage"]
        dict_final["query_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        return dict_final
    
    # data = gql(query, {"input": name})
    # if data['taxonNameMatch']:  
    #   if data["match"]:
    #       return data["match"]
    return None
    #return gql(query, {"input": name})





def get_synonyms(concept_id: str):
    
    query = """
    query ($id: String!) {
      taxonConceptById(taxonId: $id) {
        hasSynonym {
          id
          fullNameStringNoAuthorsPlain
          fullNameStringPlain
          #authorsString
        }
      }
    }
    """

    rep = gql(query, {"id": concept_id})
    if  rep is None:
      return {"error":True, "connection": False, "match": None}
    if rep["data"]["taxonConceptById"] is None:
      return {"error":False, "connection": True, "match": None}
    return {"error":False, "connection": True, "match": rep["data"]["taxonConceptById"]["hasSynonym"]}    

    return data["data"]["taxonConceptById"]["hasSynonym"]

def get_hierarchy(concept_id: str):
    query = """
    query ($id: String!) {
      taxonConceptById(taxonId: $id) {
      pathString
      }
    }
    """
    data = gql(query, {"id": concept_id})
    return data["data"]["taxonConceptById"]







def get_taxon_match(name: str):
    query = """
    query ($input: String!) {
      taxonNameMatch(inputString: $input) {
        error
        match {
          id
          fullNameStringNoAuthorsPlain
          authorsString
          rank
          role
          currentPreferredUsage {
            id
          }
        }
      }
    }
    """
    rep = gql(query, {"input": name})
    if rep is None:
        return {"error":True, "connection": False, "match": None}
    if not rep["data"]["taxonNameMatch"]["match"]:
        return {"error":False, "connection": True, "match": None}
    return rep["data"]["taxonNameMatch"]

def get_children(name: str):
    #return a list of children taxa of the input name, if name is accepted then return children of the accepted name
    res = get_taxon_match(name)

    if res["error"] or not res["match"]:
        return None

    match = res["match"]
    concept_id = match.get("currentPreferredUsage", {}).get("id")

    if not concept_id:
        return None

    def _generator():
        yield {
            "id": concept_id, #match["currentPreferredUsage"]["id"], #match["id"],
            "taxaname": match["fullNameStringNoAuthorsPlain"],
            "authors": match["authorsString"],
            "rank": match["rank"].capitalize(),
            "id_parent": -1,
            "id_taxonref" : 0
        }

        children = get_children_by_id(concept_id)

        for child in children or []:
            name = child.get("hasName")
            if not name:
                continue

            yield {
                "id": child["id"], #name["id"],
                "taxaname": name["fullNameStringNoAuthorsPlain"],
                "authors": name["authorsString"],
                "rank": name["rank"].capitalize(),
                "id_parent": concept_id #match["id"]
            }

    return list(_generator())











def get_taxa_fuzzy(name: str):
#query wfo to get fuzzy names matching with input name
#return match as a list of matching name and concept name
    query = """
    query ($input: String!) {
      taxonNameMatch(
      inputString: $input
      fuzzyNameParts: 1
      # checkRank:false
      # fallbackToGenus:false
      ) {
       match {
          id
          fullNameStringPlain
          currentPreferredUsage {
            id
            pathString
            hasName {
              fullNameStringNoAuthorsPlain
              authorsString
              rank
            }            
          }
        }
       candidates {
          id
          fullNameStringPlain
          currentPreferredUsage {
            id
            hasName {
              fullNameStringNoAuthorsPlain
              authorsString
              rank
            } 
          }
        }
         
      }
    }
    """

    rep = gql(query, {"input": name})["data"]["taxonNameMatch"]
    if  rep is None:
      return {"error":True, "connection": False, "match": None}
    #iif match is none, then match = candidates
    if rep["match"] is None:
      return {"error":False, "connection": True, "match": rep["candidates"]}
    return {"error":False, "connection": True, "match": [rep["match"]]}



def get_children_by_id(concept_id: str):
    #return a list of children taxa of the input concept_id
    query = """
    query ($id: String!) {
      taxonConceptById(taxonId: $id) {
      #pathString
        hasPart {
          id
          #title
          hasName {
            # id
            # fullNameStringPlain
            fullNameStringNoAuthorsPlain
            authorsString
            rank
          }
        #   hasSynonym {
        #   fullNameStringNoAuthorsPlain
        #   fullNameStringPlain
        # }
        }
      }
    }
    """
    rep = gql(query, {"id": concept_id})
    if  rep is None:
      return {"error":True, "connection": False, "match": None}
    if rep["data"]["taxonConceptById"] is None:
      return {"error":False, "connection": True, "match": None}
    return {"error":False, "connection": True, "match": rep["data"]["taxonConceptById"]}

def get_parent_by_id(concept_id: str):
    query = """
    query ($id: String!) {
      taxonConceptById(taxonId: $id) {
        path {
          id
          hasName {
            id
            fullNameStringNoAuthorsPlain
            authorsString
            rank
          }
        }
      }
    }
    """
    rep = gql(query, {"id": concept_id})
    if  rep is None:
      return {"error":True, "connection": False, "match": None}
    if rep["data"]["taxonConceptById"] is None:
      return {"error":False, "connection": True, "match": None}
    return {"error":False, "connection": True, "match": rep["data"]["taxonConceptById"]}
















def get_wfo_synonyms(concept_id: str):
    #return a list of synonyms taxa of the input concept_id, return a list of synonyms with id, taxaname, authors, rank and id_parent
    if not concept_id:
      return None
    res = get_synonyms(concept_id)
    if res["error"] or not res["match"]:
      return res
    result = []
    for syno in res["match"] or []:
        # taxaname = syno.get("fullNameStringNoAuthorsPlain")
        # taxonref = f"{taxaname} {syno.get('authorsString') or ''}".strip()
        result.append(
            {"taxaname" : syno.get("fullNameStringNoAuthorsPlain"),
             "taxonref" : syno.get("fullNameStringPlain")
            }
        )
    return {"error":False, "connection": True, "match": result}


def get_wfo_taxon(name: str):
    res = get_taxon_match(name)

    if res["error"] or not res["match"]:
        return res

    match = res["match"]
    concept_id = match.get("currentPreferredUsage", {}).get("id")
    return { "error": False, "connection": True,
            "match":{
            "id": concept_id,
            "taxaname": match["fullNameStringNoAuthorsPlain"],
            "authors": match["authorsString"] or "",
            "rank": match["rank"],
            "id_parent": -1}
        }
def get_wfo_children(concept_id: str):
    #return a list of children taxa of the input concept_id, return a list of children with id, taxaname, authors, rank and id_parent
    if not concept_id:
      return None
    res = get_children_by_id(concept_id)
    if res["error"] or not res["match"]:
        return res
    result = []
    children = res["match"]["hasPart"]
    for child in children or []:
        name = child.get("hasName")
        if not name:
            continue

        result.append( {
            "id": child["id"],            
            "taxaname": name["fullNameStringNoAuthorsPlain"],
            "authors": name["authorsString"] or "",
            "rank": name["rank"],
            "id_parent": concept_id,
            "id_taxonref" : 0
        })
    res["match"] = result
    return res

def get_wfo_parents(concept_id: str):
  #return hierarchy of parents of the input concept_id, return a list of parents with id, taxaname, authors, rank and id_parent
    if not concept_id:
      return None
    res = get_parent_by_id(concept_id)
    if res["error"] or not res["match"]:
        return res
    result = []
    parents = res["match"]["path"]

    id_parent = -1
    for parent in parents[-2::-1] or []:
        name = parent.get("hasName")
        if not name:
            continue
        result.append( {
            "id": parent["id"], 
            "taxaname": name["fullNameStringNoAuthorsPlain"],
            "authors": name["authorsString"] or "",
            "rank": name["rank"],
            "id_parent": id_parent
        })
        id_parent = parent["id"]
    res["match"] = result
    return res


def wfo_get_fuzzy_names(name: str):
#return match as a list of taxa fuzzy matching input name (id, name and taxaname)
#id = concept_id of taxaname, if accepted then name=taxaname
  rep = get_taxa_fuzzy(name)
  candidates = []
  if rep["match"]:
    for match in rep["match"]:        
        concept_match = match.get("currentPreferredUsage", None)
        if concept_match:
          concept_id = concept_match.get("id")
          concept_name = concept_match.get("hasName")
          candidates.append ({
              "id": concept_id,
              "fuzzyname": match["fullNameStringPlain"],
              "taxaname": concept_name["fullNameStringNoAuthorsPlain"],
              "authors": concept_name["authorsString"] or "",
              "accepted" : concept_id.startswith(match.get("id")),
              "rank": concept_name["rank"]
          })
    return {"error":False, "connection": True, "match": candidates}
  else:
      return rep








#print (wfo_get_fuzzy_names("miconia"))
#print (get_wfo_children ("wfo-4000024014-2026-06"))




#print (get_taxon_match ("Stephanotrichum"))
#print (resolve_name_id ("miconio calvesce"))

#print (get_metadata ("wfo-4000040307"))
#print (get_wfo_synonyms ("wfo-1000005274-2026-06"))
#print (get_children ("Melastomataceae"))
#print (get_metadata (resolve_name_id ("Mic ca")))
#print (resolve_taxon_metadata ("Miconia calvescens"))
#print (get_wfo_children ("wfo-7000000372-2026-06"))
#print (get_wfo_taxon ("Miconia calvescens")) #wfo-0001078818-2026-06
#print (get_wfo_taxon ("Melastomataceae")) #wfo-7000000372-2026-06print (get_wfo_parents ("wfo-0001078818-2026-06"))
#print (get_children_by_id("wfo-7000000372-2026-06"))
#introspect_type ("TaxonName")
#print (get_wfo_children("wfo-0001078818-2026-06"))

# query = """
# {
#   __schema {
#     queryType {
#       fields {
#         name
#         args {
#           name
#           type {
#             kind
#             name
#             ofType {
#               kind
#               name
#               ofType {
#                 kind
#                 name
#               }
#             }
#           }
#         }
#       }
#     }
#   }
# }
# """ 

#print(gql(query))


# query = """
# {
#   __type(name: "NameMatchResponse") {
#     fields {
#       name
#       type {
#         kind
#         name
#         ofType {
#           kind
#           name
#         }
#       }
#     }
#   }
# }
# """

