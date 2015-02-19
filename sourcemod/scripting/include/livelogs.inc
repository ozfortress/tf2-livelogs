/*
    Livelogs server plugin includes
    
    Copyright (C) 2012 Prithu "bladez" Parker

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>
*/

#define RED 0
#define BLUE 1
#define TEAM_OFFSET 2

#define BITMASK_DAMAGE_TAKEN 1 //bit value of DAMAGE_TAKEN                                
#define BITMASK_DAMAGE_DEALT 2
#define BITMASK_HEALING 4
#define BITMASK_ITEM_PICKUP 8
#define BITMASK_MEDIC_BUFF 16

/*
    Take a TFClassType enum and convert it to a class name string
*/
stock bool:TF2_GetClassName(TFClassType:class, String:name[], maxlen)
{
    switch (class)
    {
        case TFClass_Unknown:
            return false;
        
        case TFClass_Scout:
        {
            strcopy(name, maxlen, "scout");
            return true;
        }
        
        case TFClass_Soldier:
        {
            strcopy(name, maxlen, "soldier");
            return true;
        }
        
        case TFClass_Pyro:
        {    
            strcopy(name, maxlen, "pyro");
            return true;
        }

        case TFClass_DemoMan:
        {    
            strcopy(name, maxlen, "demoman");
            return true;
        }

        case TFClass_Heavy:
        {    
            strcopy(name, maxlen, "heavyweapons");
            return true;
        }

        case TFClass_Medic:
        {    
            strcopy(name, maxlen, "medic");
            return true;
        }

        case TFClass_Sniper:
        {    
            strcopy(name, maxlen, "sniper");
            return true;
        }

        case TFClass_Engineer:
        {    
            strcopy(name, maxlen, "engineer");
            return true;
        }
        case TFClass_Spy:
        {
            strcopy(name, maxlen, "spy");
            return true;
        }
    }

    return false;
}
