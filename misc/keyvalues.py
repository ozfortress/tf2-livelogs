#custom exception when an invalid keyvalues file is detected
class InvalidKeyValueData(Exception):
    pass

class KeyValues(object):
    """
    a class for parsing keyvalue data
    this class can be reused an infinite number of times, without having to create a new object every time
    it is necessary to parse keyvalues

    see items.txt in /misc/ for an example keyvalues file
    """
    def __init__(self):
        self._kv_dict = {}
        self._buf_position = 0

        self._block_begin = "{"
        self._block_end = "}"

    def parse(self, data):
        self.__init__()

        #takes a set of KV as data, and parses it into a python dict
        self._buffer = data

        curr_string = ""
        curr_key = ""

        while self._buf_position < len(self._buffer):
            self._skip_whitespace() #skip all whitespace until we get to the next valid chunk

            if self._curr_bit() == self._block_begin:

            elif self._curr_bit() == self._block_end:

            else:
                #this is a string
                curr_string = self._read_string()




    def _read_string(self):
        #read out a string section of the key values

        string_quoted = False
        char_escaped = False

        if self._curr_bit() == "\"" and not string_quoted:
            #we have a " at the start of the string, so it is therefore quoted
            string_quoted = True

            self._goto_next_bit() #skip to the next bit, which will be the beginning of the string

        while True:
            curr_bit = self._curr_bit()

            if curr_bit == None:
                self.__raise_exception("Reached end of buffer inside token")

            if curr_bit == self._block_begin or curr_bit == self._block_end and not string_quoted:
                self.__raise_exception("Block symbol in non-quoted token")

            if curr_bit == "\"":
                if string_quoted

                

            if curr_bit == "\\":
                #this character is a backslash, so the next character will be escaped
                char_escaped = True #mark the next character for escaping

                self._goto_next_bit()

                continue




    def _skip_whitespace(self):
        #moves the buffer position forward until non-whitespace characters are encountered
        while True:
            if self._curr_bit() not in ['\n', '\t', ' ', '\r']:
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

    def _goto_next_bit(self):
        self._buf_position += 1

    def __raise_exception(self, message):
        raise InvalidKeyValueData("%s at position %d" % (message, self._buf_position))