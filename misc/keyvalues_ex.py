import collections

class KeyValues(collections.MutableMapping):
    """Class for representing Key Values objects, with container behavior.

    This class implements the tree data structure used by KeyValues, exposing
    method for acting like a python Dictionary, but keeping the key order.

    It also implements methods for representing its data as a string.
    """

    def __init__(self, name=""):
        self._parent = None
        self._children = collections.OrderedDict()

        self._name = name

    # Container interface
    def __contains__(self, key):
        return key in self._children

    # Iterable interface
    def __iter__(self):
        return iter(self._children)

    # Sized interface
    def __len__(self):
        return len(self._children)

    # Mapping interface
    def __getitem__(self, key):
        return self._children[key]

    # MutableMapping interface
    def __setitem__(self, key, value):
        if isinstance(value, KeyValues):
            value._parent = self
        self._children[key] = value

    def __delitem__(self, key):
        del self._children[key]

    # String conversion
    def __str__(self):
        return self.stringify()

    def _escape(self, text):
        for char in "\\\"":
            text = text.replace(char, '\\' + char)
        return text


    def parent():
        """Return the parent object for this KeyValues
        """

        return self._parent

    def load(self, obj):
        """Load the KeyValues from the given object
        """

        tokenizer = KeyValuesTokenizer(obj.read())

        token = tokenizer.next_token()
        if not token or token["type"] != "STRING":
            # TODO: make a better explanation
            raise Exception("Invalid token")

        self.__init__(token["data"])

        token = tokenizer.next_token()
        if not token or token["type"] != "BLOCK_BEGIN":
            print "token: %s" % token
            # TODO: make a better explanation
            raise Exception("Invalid token")

        self._parse(tokenizer)

        # We should have nothing left
        if tokenizer.next_token():
            raise Exception("Unexpected token at file end")

    def _parse(self, tokenizer):
        key = None

        while True:
            token = tokenizer.next_token()
            if not token:
                raise Exception("Unexpected file end")

            if key:
                if token["type"] == "BLOCK_BEGIN":
                    value = KeyValues(key)
                    value._parse(tokenizer)
                    self[key] = value
                elif token["type"] == "STRING":
                    self[key] = token["data"]
                else:
                    # TODO: make a better explanation
                    raise Exception("Invalid token" + token["type"])
                key = None
            else:
                if token["type"] == "BLOCK_END":
                    break
                if token["type"] != "STRING":
                    # TODO: make a better explanation
                    raise Exception("Invalid token")
                key = token["data"]


class KeyValuesTokenizer:
    """Parser for KeyValuesTokenizer

    This class is not meant to external use
    """

    def __init__(self, b):
        self._buffer = b
        self._position = 0
        self._last_line_break = 0
        self._line = 1

    def next_token(self):
        while True:
            self._ignore_whitespace() #loop through whitespace until non-whitespace char

            if not self._ignore_comment(): #ignore comments
                break

        # get the first char after whitespace/comments
        current = self._current()
        if not current:
            return False

        # Emit any valid tokens
        if current == "{": #current char is a block starter
            self._forward() #move to the next bit for the next read
            return {"type": "BLOCK_BEGIN"} #return block type
        elif current == "}": #current char is a block ender
            self._forward()
            return {"type": "BLOCK_END"}
        else:
            data = self._get_string() #data must be a string, so get the string data
            return {"type": "STRING", "data": data}

    def _get_string(self):
        escape = False
        result = ""

        quoted = False
        if self._current() == "\"": #we're at the beginning of non-whitespace. if the char is a ", then the string is quoted
            quoted = True
            self._forward() #next byte

        while True:
            current = self._current()

            # if we're out of characters, break
            if not current:
                break

            #curely braces cannot be in non-quoted strings
            if not quoted and current in ['{', '}']:
                break

            # Check if it's the end of a quoted string
            if not escape and quoted and current == '"':
                #if we didn't detect an escape (\) in the prev char and there is a " and the string is quoted this means it's the end of the string
                #therefore, break

                break

            # Add the character or escape sequence to the result
            if escape:
                #if we detected a \ in the prev char, we're escaping this char
                escape = False

                if current == "\"":
                    result += "\"" #add the escaped "

                elif current == "\\": #add the escaped \
                    result += "\\"

            elif current == "\\": #if the current char is a \, set escape to True to that we know to escape the next char
                escape = True
            else:
                result += current #add the current char to the result

            self._forward()

        if quoted: #skip the end of the quoted string ("), and go to the next byte
            self._forward()

        return result #return str

    def _ignore_whitespace(self):
        while True:
            current = self._current() #get current byte

            if not current:
                break

            if current == "\n":
                # Keep track of this data for debug
                self._last_line_break = self._position
                self._line += 1

            if current not in [' ', '\n', '\t']: 
                #if the current char is not a whitespace character, break to indicate end of whitespace
                break

            self._forward() #move forward 1 byte in the buffer


    def _ignore_comment(self):
        if self._current() == '/' and self._next() == '/': #if it's a comment (//blah, skip ahead to \n)
            while self._current() != "\n":
                self._forward()

            return True

        return False

    def _current(self):
        if self._position >= len(self._buffer):
            return None

        return self._buffer[self._position]

    def _next(self):
        if (self._position + 1) >= len(self._buffer):
            return None

        return self._buffer[self._position + 1]

    def _forward(self):
        self._position += 1
        return (self._position < len(self._buffer))

    def _location(self):
        return "line {0}, column {1}".format(self._line, (self._position - self._last_line_break))