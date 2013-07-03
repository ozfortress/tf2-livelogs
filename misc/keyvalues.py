#custom exception when an invalid keyvalues file is detected
class InvalidKeyValueData(Exception):
    pass

class KeyValues(object):
    """
    a class for parsing keyvalue data

    see items.txt in /misc/ for an example keyvalues file
    """
    def __init__(self, position = 0):
        self._kv_dict = {}
        self._buf_position = position

        self._block_begin = "{"
        self._block_end = "}"
        self.__whitespace_chars = ['\n', '\t', ' ', '\r']

    def parse(self, data):
        #takes a set of KV as data, and parses it into a python dict
        #returns the dictionary of the data parsed
        self._buffer = data

        prev_string = None
        curr_key = None
        curr_dict = {}

        while self._buf_position < len(self._buffer):
            prev_string = curr_key #remember the last string read

            self._skip_whitespace() #skip all whitespace until we get to the next valid chunk

            if self._curr_bit() == self._block_begin:
                if curr_key is None:
                    self.__raise_exception("Expected token, but instead found '{'")
                else:
                    #this marks the beginning of a block, and we have a string, so we can safely assume it is the starting of a key

                    #we recursively parse the lower levels of the data
                    self._goto_next_bit() #move to the bit after '{' before recursion
                    new_kv = KeyValues(self._buf_position)
                    new_value = new_kv.parse(self._buffer)
                    self._buf_position = new_kv._buf_position #move the buffer position up to what was read by the lower recursion

                    curr_dict[curr_key] = new_value
                    curr_key = None

            elif self._curr_bit() == self._block_end:
                #end of a block has been reached, so break out of this recursion, allowing a higher level to run further
                self._goto_next_bit() #skip over the end block char
                break

            else:
                #this is a string
                curr_key = self._read_string()
                if prev_string:
                    #prev_string is the key of a data string, and curr_key is the value
                    curr_dict[prev_string] = curr_key

                    #clear both vars for next read
                    prev_string = None
                    curr_key = None

            self._kv_dict = curr_dict

        return self._kv_dict


    def _read_string(self):
        #read out a string section of the key values
        string_quoted = False

        rtn_string = ""

        if self._curr_bit() == "\"":
            #we have a " at the start of the token, so it is therefore quoted
            string_quoted = True

            #self._goto_next_bit() #skip to the next bit, which will be the beginning of the token's data

        while self._goto_next_bit():
            curr_bit = self._curr_bit()

            if curr_bit == None:
                self.__raise_exception("Reached end of buffer inside token")

            if curr_bit == self._block_begin or curr_bit == self._block_end and not string_quoted:
                self.__raise_exception("Block symbol in non-quoted token")

            if curr_bit == '"':
                if string_quoted and self._prev_bit() == "\\":
                    #escaped ", so add it to the string
                    rtn_string += curr_bit
                elif self._next_bit() not in self.__whitespace_chars:
                    #the quote marks the end of the string, because it is not escaped
                    #the next bit is not whitespace, but this quote should have ended the token, so the data is invalid
                    self.__raise_exception("Expected whitespace at end of token")
                else:
                    self._goto_next_bit() #move to the end of the token for the next reading chunk
                    break

            elif curr_bit == "\\" and self._prev_bit() == "\\":
                #this is an escaped backslash, so add it to the string
                rtn_string += curr_bit
                
                #else:
                    #perhaps this character escapes the next character

            elif curr_bit in self.__whitespace_chars and not string_quoted:
                #this token is not quoted, and this is a whitespace char. therefore, the token ends here.
                self._goto_next_bit() #move the position to the bit after the end of the token
                break

            else:
                rtn_string += curr_bit

        return rtn_string


    def _skip_whitespace(self):
        #moves the buffer position forward until non-whitespace characters are encountered
        while True:
            if self._curr_bit() not in self.__whitespace_chars:
                #if the char is not a whitespace char, break
                break
            
            else:
                #else, move to the next char
                self._goto_next_bit()

    def _curr_bit(self):
        if self._buf_position >= len(self._buffer):
            return None

        else:
            return self._buffer[self._buf_position]

    def _prev_bit(self):
        if self._buf_position > 0:
            return self._buffer[self._buf_position - 1]
        else:
            return None

    def _next_bit(self):
        if (self._buf_position + 1) < len(self._buffer):
            return self._buffer[self._buf_position + 1]
        else:
            return None

    def _goto_next_bit(self):
        #return True if we've moved to the next bit, false if not
        if self._next_bit(): #if next bit exists
            self._buf_position += 1 #increment buffer position
            return True

        else:
            return False

    def __raise_exception(self, message):
        raise InvalidKeyValueData("%s at position %d" % (message, self._buf_position))

