import logging

import keyvalues

class Steam_API(object):
    def __init__(self):
        self.__api_key = "7CD8EC56801BD2F23A1A4184A1348ADD"

        self.__item_data_url = None

        self._items_game_data = None

    def get_item_data_loc(self):
        logging.info("Getting SAPI items_game.txt location")

        steam_item_url = "http://api.steampowered.com/IEconItems_440/GetSchema/v0001/?key=%s&format=json" % (self.__api_key)
        api_res = urllib2.urlopen(steam_item_url) #retrieve the items data

        api_res_dict = json.load(api_res) #load the json result into a dict

        if api_res_dict and ("result" in api_res_dict):
            #we only want the items_game.txt from the api query
            if "items_game_url" in api_res_dict["result"]:
                items_game_url = api_res_dict["result"]["items_game_url"]

                self.__item_data_url = items_game_url

                logging.info("SAPI items_game.txt URL: %s", items_game_url)

                return True #able to get items_game.txt url

        return False #not able to get url

    def get_default_weapons(self):
        weapon_dict = {}
        #add static weapon names to the dict, that for whatever reason aren't in items_game.txt
        weapon_dict["scout"] = [ "scattergun", "pistol_scout", "bat" ]
        weapon_dict["soldier"] = [ "tf_projectile_rocket", "rocketlauncher_directhit", "shotgun_soldier", "shovel" ]
        weapon_dict["pyro"] = [ "flamethrower", "shotgun_pyro", "fireaxe", "flaregun", "deflect_flare", "deflect_promode",
                                 "deflect_rocket", "deflect_sticky", "taunt_pyro" ]

        weapon_dict["demoman"] = [ "tf_projectile_pipe", "tf_projectile_pipe_remote", "sword", "bottle" ]
        weapon_dict["heavyweapons"] = [ "minigun", "shotgun_hwg", "fists", "taunt_heavy" ]
        weapon_dict["medic"] = [ "syringegun_medic", "bonesaw" ]
        
        weapon_dict["sniper"] = [ "sniperrifle", "smg", "club", "tf_projectile_arrow", "compound_bow", "taunt_sniper" ]
        weapon_dict["engineer"] = [ "shotgun_primary", "pistol wrench", "obj_sentrygun", "obj_sentrygun2", "obj_sentrygun3" ]
        weapon_dict["spy"] = [ "revolver", "knife" ]

        return weapon_dict

    def get_item_data(self):
        #get the latest item schema from the steam API

        weapon_dict = self.get_default_weapons()

        if not self.__item_data_url:
            logging.info("Don't have item_games.txt URL, using static weapons")
            return weapon_dict

        logging.info("Getting item data")
        
        items_game_res = urllib2.urlopen(self.__item_data_url)

        kv_parser = keyvalues.KeyValues()

        items_game_data = kv_parser.parse(items_game_res.read()) #turn the items_game.txt result into a dict


        if not items_game_data:
            logging.info("Unable to get item data. Using only static weapon data")
            return weapon_dict

        self._items_game_data = items_game_data

        logging.info("Item data received. Populating weapon dict with non-static weapons")        

        if "items" in items_game_data["items_game"]:
            #we have all items in a dictionary! now let's loop over them
            item_dict = items_game_data["items_game"]["items"]
            for item_key in item_dict:
                item = item_dict[item_key]

                if "used_by_classes" in item and "item_logname" in item:
                    item_classes = item["used_by_classes"]
                    for pclass_u in item_classes:
                        #now we have individual classes per item
                        pclass = pclass_u.encode('ascii', 'ignore') #convert the class name to plain ASCII instead of unicode
                        if pclass not in weapon_dict:
                            weapon_dict[pclass] = [ item["item_logname"].encode('ascii', 'ignore') ] #convert item name to ASCII before adding
                        else:
                            weapon_dict[pclass].append(item["item_logname"].encode('ascii', 'ignore')) #convert item name to ASCII before adding

        #move "heavy" to "heavyweapons", because the game uses the latter rather than the former
        weapon_dict["heavyweapons"] += weapon_dict["heavy"]
        del weapon_dict["heavy"] #remove old key

        logging.info("Weapon dict populated with non-static weapons")

        return weapon_dict