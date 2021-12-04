"""
    Filename: ada.py
     Version: 4.0
      Author: Richard E. Rawson
        Date: 2021-10-09
 Description: Command line RPN calculator that performs a variety of common functions. This program contains 96 functions that are needed for the operation of the calculator itself, along with help functions and other utility functions such as conversions.

Program and package information:
            OS: Windows 10 10.0.19041 SP0
        curses: 2.2
          json: 2.0.9
     pyperclip: 1.8.2
        python: 3.8.0

Versions:
    1.0 -- The original draft version of ada.
    2.0 -- Major update to the original version.
    3.0 -- Updated by incorporating "curses".
    4.0 -- Re-code for conciseness and better coding.

v4.0 is the version available as "master" on github.
"""

import curses
from decimal import Decimal, InvalidOperation
import json
import math
import operator
from pprint import pprint
import pyperclip as pc  # for copying text (the command line) to the clipboard
import random
import statistics
import textwrap
from string import ascii_letters, ascii_lowercase, ascii_uppercase, digits


# ==== TODOLIST========================================================================

# FEATURE:
# -- Save memory registers between sessions.


# =====================================================================================


# ==== MAIN CALCULATOR FUNCTION =============================


def RPN(stack, user_dict, lastx_list, mem, settings, tape, window):
    """
    Main function that:
        1. prints the register and a short menu on screen
        2. gets the user's input
        3. does initial processing, so we know what to do with whatever the user enters
        3. ...otherwise, we stay in the while... loop

    User inputs can be any of the following:
        -- one or more numbers with or without one or more operators (e.g., +, x, sqrt)
        -- groups of numbers/operators, delimited with parentheses
        -- hex or binary numbers or rgb/hex values
        -- memory register operator
        -- one or more commands (e.g., index, set, drop, swap)
        -- one or more shortcut commands (e.g, s, d, c)
        -- a user-defined operator (expression or constant)
        -- a named constant (e.g, avogadro, parsec)
        -- a transparency value (%) for hex colors
        -- other inputs that cannot be processed at all (e.g, "claer" (not "clear"), or unbalanced parentheses)

        Some inputs can be handled easily within this function, but most require further processing by process_item() which will return a [list] of individual items that the user entered.

    Args:
        stack (list): the stack
        user_dict (dict): user-defined operations
        lastx_list (list): running list of x: values stored in a list
        mem (dict): dictionary of memory registers
        settings (dict): settings used by the program
        tape (list): list of entered_values, entered by the user
        window (_curses.window): terminal window

    Raises:
        Exception: handles "h" and "h q" entries so the program doesn't choke

    Returns: None
    """

    # Make sure the terminal environment is what we want.
    curses.noecho()
    curses.flushinp()
    window.clear()
    window.refresh()

    while True:
        quit = False

        # Print the register.
        stack = print_register(stack, settings, window)

        # Generate and print the menu after printing the register.
        window.addstr('\n')
        for i in range(0, len(menu), 4):
            m = ''.join(menu[i:i+4])
            window.addstr(m + '\n')
        window.refresh()
        start_row = 8

        # Get the command line entry from the user. We can't do lower() because the MEM
        # functions depend on uppercase entries.
        entered_value, entered_list = '', []
        entered_value = get_user_input(window, start_row, 0, "").lstrip().rstrip()

        # If the user enters "q", then quit.
        if entered_value.lower().strip() == 'q':
            return

        # Make sure that any parentheses are paired before proceeding.
        lst = list(entered_value)
        if lst.count('(') - lst.count(')') != 0:
            window.addstr('\nParentheses are not balanced. ')
            input = get_user_input(window, None, None, "Press <ENTER> to continue...")
            window.refresh()
            continue

        # If <ENTER> alone was pressed, duplicate the x: value on the stack
        # and then loop back with <continue>.
        if len(entered_value) == 0:
            x = stack[0]
            stack.insert(0, x)
            continue

        # ==== HERE, WE BEGIN PARSING "entered_value", THE USER'S COMMAND-LINE INPUT.
        """
        Step 1 in processing is to take care of inputs that can be handled easily. These include:
            -- user-defined operations (these are required to be on their own line)
            -- a hex color beginning with a '#'
            -- a hexadecimal value, beginning with '0x'
            -- a binary number beginning with "0b"

        Step 2 is to parse more complex command line entries, which includes anything that couldn't be parsed in Step 1. What a user may enter on the command line is very flexible and unpredictable, including any combination of parentheses, floats, integers, math operators (e.g, (45 32 -) 5 x 9 / 273.15 +), or other commands such as "about" or "advanced". Such command lines need to be parsed into the individual items. Then the program can determine what to do with each item via initial_processing() and process_item().
        """

        # If "entered_value" is in {phrases}, translate "entered_value" here before continuing. This allows entering a phrase rather than a shortcut. Example: "grams to ounces" rather than "go". The former makes more sense; the latter is faster.
        if entered_value.lower() in phrases.keys():
            entered_value = phrases[entered_value.lower()][0]

        # Get the user-defined operation, itself, and make THAT the "entered_value".
        if entered_value in user_dict.keys():
            entered_value = str(user_dict[entered_value][0])

        # If "entered_value" is a hex color beginning with a '#', convert to RGB.
        if entered_value[0] == '#':
            stack = hex_to_rgb(stack, entered_value, window)

        # If "entered_value" is a hexadecimal value, beginning with '0x', convert to a decimal.
        elif entered_value[0:2] == '0x':
            stack = convert_hex_to_dec(stack, window, entered_value.split(' ')[0][2:])

        # If "entered_value" is a binary number beginning with "0b", convert to a decimal.
        elif entered_value[0:2] == '0b':
            stack = convert_bin_to_dec(stack, window, entered_value.split(' ')[0][2:])

        # CODENOTE: Except for the special cases above, we're going to have to parse what the user entered.
            # -- First, we will get each item (defined as whatever is between spaces) and put each item into a list.
            # -- Second, once we have a list of items, we can figure out what to do with each item.
        else:
            stack, entered_list = parse_entry(stack, entered_value)

            # ! This is the single line of code that will handle the vast majority of inputs.
            stack, lastx_list, tape, user_dict, settings = initial_processing(window, stack, entered_list, lastx_list, user_dict, mem, settings, tape)

        # Append the command line to the tape. Since some commands, like "0b..." or "0x...", don't go through "entered_list", add those commands from "entered_value"
        if entered_list:
            tape.append(entered_list)
        else:
            tape.append(entered_value)

        if quit:
            # Save {settings} to disk before quitting.
            with open('config.json', 'w+') as file:
                file.write(json.dumps(settings, ensure_ascii=False))
            window.addstr('\nEnd program.\n')
            window.refresh()
            break

    return None


# ==== EXPRESSION EVALUATION FUNCTIONS =============================


def parse_entry(stack, entered_value):
    """
    Take whatever the user entered on the command line as "entered_value", parse out each element. Put each distinct element (character/operator/number) of the user's entered_value into a list.

    Example: Each of the following characters, delimited by spaces, is a single element that will be added to [entered_list]:

    (43 62 s d dup +) --> ['(', '43', '62', 's', 'd', 'dup', '+, ')']

    This fxn has the challenge of figuring out exactly WHAT string of characters qualifies as a single item. For example, in the above expresson, "d" as a lone character is one item while the 'd' in 'dup' belongs with 'up' to form "dup" as one item. So, we can't just use str.split(). Further, we can't always count on the user using spaces appropriately. For example, "3 5+" is a valid entry, but str.split(" ") will yield ["3", " ", "5+"] and that won't process well.

    Arguments:
        entered_value (str) -- the string that the user entered

    Return:
        entered_list [list] -- list of actionable items returns to RPN()
    """

    """
    entered_list [list] -- stores each "actionable" item in "entered_value"
    s (string) -- stores a string that will go into "entered_list". For example, s = "drop" will be added to entered_list as "drop", but if "entered_value" contains "45.6", then s should continue to "accumulate" characters until it holds the whole number before being added to "entered_list".

    data [list] -- temporary list that accumulates the "actionable" items in "entered_value"; cleanup up to become [entered_list]
    """
    data, entered_list, s = [], [], ''

    ndx = -1
    # If the user entered a number with commas, delete the commas. This means that 3,545 will be converted to 3545. One consequence is that "3,5 +" will be converted to "35 +"  and not "3 5+" as might have been intended. The user should use spaces where spaces are intended.
    entered_value = entered_value.replace(',', '')

    # Iterate through each character in the "entered_value" string.
    while True:

        # "ndx" keeps track of where we are in the "entered_value" string.
        ndx += 1
        if ndx >= len(entered_value):
            break

        # If this item is an open or a closed parenthesis, treat it as a single item.
        if entered_value[ndx] in ['(', ')']:
            s = entered_value[ndx].strip()

        # If this item is an integer, gather all the following digits into one string Example: entered_value is "56", and this item is "5". We don't want "5" and "6" to be added to "entered_list" as separate items. For our purposes, a "number" is any part of the "entered_value" string that starts with a digit, a period, or a minus sign and ends with anything else. Example: "-43.5 " is a number. "-43.5d" enters "-43.5" on the stack and then "d"rops x:.
        elif entered_value[ndx] in digits or entered_value[ndx] == '-' or entered_value[ndx] == '.':

            while entered_value[ndx] in digits or entered_value[ndx] == '-' or entered_value[ndx] == '.':

                s += entered_value[ndx].strip()

                # Figure out what the next character in the string is. There may not be a "next character", so an exception will be raised. Once we've reached the end of the number, we have that entire number in "entered_list", so break out of this loop.
                try:
                    if entered_value[ndx+1] in digits or entered_value[ndx+1] == '-' or entered_value[ndx+1] == '.':
                        ndx += 1
                    else:
                        break
                except IndexError:
                    break

        # If this item is an alphabetic character, including a single-character command in either {op1} or {op2}, gather all the following characters into one string. Example: "trim" is a valid command, but "t" by itself is not, so we need to get the whole word "trim".
        # NOTE: the variable "letters" contains alphabetical letters + colon, underscore, !.
        elif entered_value[ndx] in letters or entered_value[ndx] in op1.keys() or entered_value[ndx] in op2.keys():

            while entered_value[ndx] in letters or entered_value[ndx] in op1.keys() or entered_value[ndx] in op2.keys():

                s += entered_value[ndx].strip()

                try:
                    if entered_value[ndx+1] in lower_letters:
                        ndx += 1
                    elif entered_value[ndx] == 'M' and entered_value[ndx+1] in ['+', '-', 'D', 'L', 'R']:
                        s += entered_value[ndx+1].strip()
                        ndx += 1
                        break
                    else:
                        break
                except IndexError:
                    break

        # if item is a register on the stack, replace with stack value
        if s in ['x:', 'y:', 'z:', 't:']:
            s = str(stack[0]) if s == 'x:' else s
            s = str(stack[1]) if s == 'y:' else s
            s = str(stack[2]) if s == 'z:' else s
            s = str(stack[3]) if s == 't:' else s

        data.append(s)
        s = ''

    # In case x:, y:, z:, t: are used, the values in those registers now reside in "entered_value", so delete them from the stack.
    for ndx, r in enumerate(['x:', 'y:', 'z:', 't:']):
        if r in entered_value:
            stack[ndx] = 0.0

    # Convert numbers to floats and strip out empty elements and punctuation (e.g., commas, as in, comma delimited number sequences).
    for i in data:
        if i in [',', ';', ':']:
            i = ' '
        if i.strip() or i in ['(', ')']:
            try:
                entered_list.append(Decimal(i))
            except:
                entered_list.append(i.strip())

    return stack, entered_list


def initial_processing(window, stack, entered_list, lastx_list, user_dict, mem, settings, tape):
    """
    Take in the parsed input in [entered_list] and, one item at a time:
        1. append to [lastx_list] to keep track of what was in the x: register last
        2. if the item is "h", then get help
        3. if the item is a shortcut, perform the action
        4. if the item is "set" then change settings
        5. if the item is anything else, then, via process_item(), perform the appropriate action or run the indicated function

    NOTE: items within parentheses are handled in the same way as items that are NOT in parentheses, except that all the items are handled AS A GROUP.

    Args:
     entered_list: [list], each item entered on the command line is one item in the list
       lastx_list: [list], running list of x: values stored in a list
              mem: {dict}, dictionary of memory registers
         settings: {dict}, dictionary of program settings
            stack: [list], holds the stack; unlimited length
             tape: [list], list of entered_values, entered by the user
        user_dict: {dict}, user-defined operations
           window: _curses.window, the terminal instance

    Raises exception: 1. user enters only "h"
                      2. user enters "h q"
    """

    # NOTE: Most commonly, user will have entered more than one item on the command line. At this point, each individual item in the command line is an item in [entered_list]. This function will process one item after another, figuring out what to do with each item. "ndx" keeps track of the item number in [entered_list].
    ndx = 0
    while ndx < len(entered_list) and len(entered_list) > 0:

        item = entered_list[ndx]

        # Save this item as lastx_list; retrieved by get_lastx().
        lastx_list = [lastx_list[-1]]
        lastx_list.append(stack[0])

        # Process shortcuts:
        if item in shortcuts.keys():

            # If "h" is by itself, show a help message.
            if item == 'h' and len(entered_list) == 1:
                window.move(8, 0)
                window.clrtobot()
                window.move(9, 0)
                window.addstr('='*45)
                window.addstr('\nFor help with individual commands, type:')
                window.addstr('\n\n     h [command]\n\n')
                window.addstr('where [command] is any command or operation.\n\nType:\n\n     index\n\nto access lists of commands and operations.\n')
                window.addstr('\nType:\n\n     basics\n\nfor help with how to use an RPN calculator\n')
                window.addstr('='*45 + '\n\n')
                window.refresh()
                input = get_user_input(window, 28, 0, "Press <ENTER> to continue...")
                window.move(8, 0)
                window.clrtobot()
                window.refresh()
                ndx = 42000  # break out of the loop

            # This elif catches the possible entry of "h q" and prevents premature quitting.
            elif item == 'q':
                ndx = 420000  # break out of the loop, forcing return to RPN()

            # If user enters "h" + (str), send (str) to help_fxn(), which will figure out what help to display.
            elif item == 'h' and len(entered_list) > 1 and entered_list[ndx+1] != 'q':
                help_fxn(stack, entered_list[ndx+1], window)
                ndx += 1

            # For any other shortcut, get the operation and then execute it.
            else:
                operation = shortcuts[item][0]
                stack = operation(stack, item, window)

        # Process any item except a shortcut or '('.
        elif item != '(' and item not in shortcuts.keys():
            # Send everything but settings to process_item().
            if item == 'set':
                settings = calculator_settings(stack, settings, window)
            else:
                stack, lastx_list, tape, user_dict = process_item(
                    stack, user_dict, lastx_list, mem, settings, tape, item, window)
            ndx += 1
            continue

        # If '(', then this is the start of a group; a result is obtained for each group.
        elif item == '(':
            while item != ')':
                stack, lastx_list, tape, user_dict = process_item(
                    stack, user_dict, lastx_list, mem, settings, tape, item, window)
                ndx += 1
                if ndx < len(entered_list):
                    try:
                        item = entered_list[ndx]
                    except:
                        pass
                continue
        else:
            pass

        ndx += 1

    return stack, lastx_list, tape, user_dict, settings


def process_item(stack, user_dict, lastx_list, mem, settings, tape, item, window):
    """
    Process a single item from [entered_list]. Essentially, this function takes an item in entered_list, which is going to be anything except a shortcut, and figures out what to do with it.

    Return:
        Modified [stack], settings, lastx_list, tape, and user_dict
    """

    # If the item is a '(' or ')', we have the start or end of a group; do nothing.
    if item in ['(', ')']:
        pass

    # If the item is a float, add it to the stack.
    elif type(item) == Decimal:
        stack.insert(0, item)

    # If the item is a math operator only requiring x:, perform the action.
    elif item in op1:
        # Several math operations catch their own exceptions, but the following catches anything I have not thought about.
        try:
            stack = math_op1(stack, item, window)
        except ValueError as error:
            window.addstr('\n' + '='*45 + '\n')
            window.addstr('Math domain error. Common examples:\n-- divide by zero\n-- square root of a negative number\n-- arccos or arcsin of value outside expeced range')
            window.addstr('\n' + '='*45 + '\n\n')
            input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    # If the item is a math operator requiring both x: and y:, perform the action.
    elif item in op2:
        stack = math_op2(stack, item, window)

    # If the operator is in {commands}, {shortcuts}, or {constants}, get the action associated with the "item". NOTE: We won't find user-defined operation names here, since those expressions have already been parsed into whatever command line the user-defined operation signifies.

    elif item in commands or item in shortcuts or item in constants or item in ['x:', 'y:', 'z:', 't:']:
        # Get just the "operation "associated with the item. We will execute the operation later.
        if item in commands:
            operation = commands[item][0]
        elif item in shortcuts:
            operation = shortcuts[item][0]
        elif item in constants:
            stack.insert(0, constants[item][0])
        else:
            pass

        # Depending on what the "item" is, perform the action.
        if item == 'lastx':
            stack = operation(stack, lastx_list, window)
        elif item == 'user':
            stack, user_dict = user_defined(stack, user_dict, window)
        elif item in ['M+', 'M-', 'MD', 'MR', 'ML']:
            stack, mem = operation(stack, mem, window)
            # NOTE: Save {mem} to a .json file after calls to any of the five memory functions. JSON does not like the decimal.Decimal number type, so keys and values are converted to strings before saving to file. When the file is read at startup, strings are converted back to decimal types.
            memory = mem.copy()
            memory = {str(k): str(v) for k, v in memory.items()}
            with open('memory_registers.json', 'w+') as file:
                file.write(json.dumps(memory, ensure_ascii=False))
        elif item == 'set':
            settings = operation(settings, window)
            return settings
        elif item == 'tape':
            entered_list = []
            tape = print_tape(window, stack, entered_list, lastx_list, user_dict, mem, settings, tape)
        elif item == 'stats':
            stack = operation(stack, settings, window)
        else:

            # CODENOTE: Here is where we execute the "operation" identified above, except for the keywords in the "if...elifs". The reason for "if item not in constants" is because, if the user entered a constant, say "e", we have already put "e" on the stack. Further, there isn't really an "operation" to execute for a constant.

            if item not in constants:
                stack = operation(stack, item, window)

    # If we get to this "else:" statement, the user entered something unrecognizable. Any unrecognized operation (a garbage entry) is ignored. The user is notified and the program simply continues.
    else:
        window.addstr('\n' + '='*45 + '\n')
        err = find_error(item)
        if err:
            window.addstr('"' + item + '"\n' + err + '\n')
        window.addstr('='*45 + '\n\n')
        window.refresh()
        input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    return stack, lastx_list, tape, user_dict


def find_error(item):
    """
    If user enters something unintelligible, try to provide some help for common errors.
    """
    if item in ['m', 'ml', 'mr', 'md', 'm+', 'm-']:
        err = 'Commands related to memory registers\nrequire capitalization.'
    else:
        err = 'Unknown command or there is a user-defined\noperation name present that needs to be on\nits own line.'
    return err


def print_register(stack, settings, window):
    """
    Display the stack register, as formatted numbers, in the terminal. Via "settings", the user can choose to display numbers in either normal or scientific format, with or without a "," separator, and with a specified number of decimal places.
    """

    stack_names = [' x', ' y', ' z', ' t']
    window.move(0, 0)
    window.clear()
    window.addstr('')

    # Get the number of decimals, the thousands separator, and the numbering format from {settings}.
    dp = settings['dec_point']
    separator = settings['separator']
    number_notation = settings['notation']

    # Stack must always have at least 4 elements.
    while len(stack) < 4:
        stack.insert(len(stack), Decimal('0.0'))

    # Make sure the stack contains only numbers. That the stack would contain anything other than a float, Decimal or int is very unlikely (impossible?), but if it did, it would be a disaster.
    stk = list(reversed(stack))
    for ndx, i in enumerate(stk):
        try:
            r = int(i)
        except ValueError:
            stk[ndx] = Decimal('0.0')
    stack = list(reversed(stk))

    """
    If the number_notation is normal, then we need to find the longest number on the stack and format the whole stack accordingly. This means that the decimal places in the register will always line up, giving space for the longest (largest) number. Two examples:

            t:   0.0000
            z:   0.0000
            y: 456.0000
            x:  45.0000

            t:                          0.0000
            z:                          0.0000
            y: 45,624,562,456,546,234,523.0000
            x:                         45.0000

    For scientific notation, numbers under 1,000 are not printed with an exponent. Thus, alignment looks like this:

            t:   0.0000
            z: 456.0000
            y:   5.7323e+5
            x:   6.9932

    """

    if number_notation == 'normal':

        # Find the number with the most digits ahead of the decimal separator.
        indent_amount, max_commas = 0, 0
        for i in stack:

            # Whether a Decimal or a float, a very large "i" will be represented as an exponent, so we need to use format() to get the whole number.
            non_exponent = '{0:.28f}'.format(i)

            # Find the length of the number to the left of the decimal point.
            whole_number_part = non_exponent.find('.') if non_exponent.find('.') >= 0 else len(non_exponent)

            # "indent_amount" is the length of the largest number. For example, the "indent_amount" for 7832.45 is 4 and for 874.99834 is 3.
            indent_amount = whole_number_part if whole_number_part > indent_amount else indent_amount

            # If the separator is a comma, rather then None, then we need to account for the space that the commas take up.
            if separator:
                max_commas = math.ceil(whole_number_part / 3) - 1 if math.ceil(whole_number_part / 3) - 1 > max_commas else max_commas

        # Calculate the total amount by which numbers should be indented. This takes into account the length of the longest number, so all decimal points will be aligned.
        indent_amount = indent_amount + max_commas + 1

        # Print the register, from the last item to the first item.
        for i in range(3, -1, -1):
            # Create the format string for the number.
            fs = ('{:' + separator + '.0' + dp + 'f}').format(stack[i])
            # Line up decimal points.
            p = indent_amount + len(fs) - fs.find('.')
            # Print one line of the register.
            window.addstr(str(stack_names[i]) + ':' + ('{:>' + str(p) + '}').format(fs) + '\n')
            window.refresh()

    else:

        # Find the number with the most digits ahead of the decimal separator.
        indent_amount, max_commas = 0, 0
        for i in stack:

            # Find the length of the number to the left of the decimal point. Since, with scientific notation, we are always going to print numbers > 1,000 with an exponent, the number of digits to the left of the decimal will always be one for those numbers.
            if i < 1000:
                whole_number_part = str(i).find('.') if str(i).find('.') >= 0 else len(str(i))
            else:
                whole_number_part = 1

            # "indent_amount" is the length of the largest number. For example, the "indent_amount" for 732.45 is 3 and for 8748.99834 is 1. The latter is the case because in scientific notation, it will appear as 8.7490e+3
            indent_amount = whole_number_part if whole_number_part > indent_amount else indent_amount

        # Calculate the total amount by which numbers should be indented. This takes into account the length of the longest number, so all decimal points will be aligned.
        indent_amount = 3 if indent_amount > 3 else indent_amount
        indent_amount = indent_amount + 1

        # Print the register, from the last item to the first item.
        for i in range(3, -1, -1):

            # Create the format string for the number. Use normal formatting if the number is less than 1000. This avoids the cumbersome display of, say 845.6 as 8.456e+2
            if stack[i] < 1000:
                fs = ('{:' + separator + '.0' + dp + 'f}').format(stack[i])
                # Line up decimal points.
                p = indent_amount + len(fs) - fs.find('.')
                # Print one line of the register.
                window.addstr(str(stack_names[i]) + ':' + ('{:>' + str(p) + '}').format(fs) + '\n')

            else:
                # This is the formatting if we need an exponents.
                fs = ('{:' + separator + '.0' + dp + 'e}').format(stack[i])
                # Line up decimal points.
                p = indent_amount + len(fs) - fs.find('.')
                # Print one line of the register.
                window.addstr(str(stack_names[i]) + ':' + ('{:>' + str(p) + '}').format(fs) + '\n')
            window.refresh()

    window.refresh()

    return stack


# ==== IMPORT FILE FUNCTIONS =============================


def get_file_data(stack, item, window):  # command: import
    """Import a text file and put the data on the stack.

Since the stack is only a one-dimensional list of
numbers, the file that you import should contain only
one column of numbers, one number to a line. Lines that
don't contain numbers will be skipped. If you mean for
a blank line to be zero, then put a zero on that line!"""

    data_file = get_user_input(window, None, None, '\nFile name: ')
    data_file = data_file.strip()

    # Read the data file.
    try:
        with open(data_file, 'r') as f:
            file = f.readlines()

    # Notify user if no file was found.
    except FileNotFoundError:
        window.addstr('\n' + '='*55 + '\n')
        window.addstr('File not found. Stack unmodified.\n')
        window.addstr('='*55 + '\n\n')
        window.refresh()
        input = get_user_input(window, None, None, "Press <ENTER> to continue...")
        return stack

    # Read the values into the stack; skip any line that is not a number.
    stack, stack_copy, cnt = [], stack.copy(), 0
    for line in file:
        try:
            stack.append(Decimal(line.strip('\n')))
            cnt += 1
        except ValueError:
            pass
        except InvalidOperation:
            window.addstr('\nFile is not a list of only numbers.\n\n')
            input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    # In case nothing was read in, re-establish the existing stack.
    if len(stack) == 0:
        stack = stack_copy

    # Provide a report to the user
    window.addstr('\n' + '='*24 + ' REPORT ' + '='*23 + '\n')
    window.addstr('   Lines in file:' + str(len(file)) + '\n')
    window.addstr('Numbers imported:' + str(cnt) + '\n')
    window.addstr('='*55 + '\n\n')
    window.refresh()

    input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    return stack


# ==== FUNCTIONS THAT PRINT THE VARIOUS DICTIONARIES (i.e., {math}, {shortcuts}) ====

def manual(stack, item, window):  # command: index
    """Menu to access the various parts of the index."""
    txt, line_width = ' INDEX ', 45
    ctr1 = math.floor((line_width - len(txt)) / 2)
    ctr2 = math.ceil((line_width - len(txt)) / 2)
    window.addstr('\n' + '='*ctr1 + txt + '='*ctr2 + '\n')
    window.addstr(
        '<com>mands and stack operations\n' +
        '<math> operations\n' +
        '<short>cuts\n' +
        '<con>stants/conversions\n' +
        '<user>-defined <op>erations\n' +
        '<phrases>\n')

    window.addstr('='*line_width + '\n')
    window.addstr("\nPress <ENTER> to continue...")
    window.refresh()

    input = get_user_input(window, 19, 29, "")

    return stack


def print_commands(stack, item, window):  # command: com
    """List commands that are not "math functions" (like add,
subtract, etc.). Rather, "commands" perform functions
that provide information, change settings, access help,
manipulate the stack, etc.

To get a list of commands, math operations, shortcuts,
constants, user-defined operations, or phrases type:

    com --> (commands)

    math --> (math operations)

    short --> (shortcuts)

      con --> (built-in constants)

    userop --> (user-defined operations)

    phrases --> (defined phrases)"""

    # print all the keys in {shortcuts}
    txt, line_width = ' COMMANDS ', 56
    ctr1 = math.floor((line_width - len(txt)) / 2)
    ctr2 = math.ceil((line_width - len(txt)) / 2)
    window.addstr('\n' + '='*ctr1 + txt + '='*ctr2 + '\n')
    window.refresh()

    print_info_utility(window, commands)

    return stack


def print_phrases(stack, item, window):       # command: phrases
    """
List all the phrases that can be used instead of
shortcuts when doing conversions. Most of the
conversions use shortcuts such as "og" (ounces to
grams). "phrases" allows the user to use the phrase
rather than the shortcut. To a large extent, the
phrases make more sense, but the shortcut is faster
to type.

IMPORTANT:
    (1) Phrases must be used alone on the command line
since they comprise two or more separate words.
    (2) Phrases are not case-sensitive.

Example:
    Put 16 on the stack:

        t: 0.00
        z: 0.00
        y: 0.00
        x: 16

    ounces to grams (or use: og)

        t: 0.00
        z: 0.00
        y: 0.00
        x: 453.5924

To get a list of commands, math operations, shortcuts,
constants, user-defined operations, or phrases type:

    com --> (commands)

    math --> (math operations)

    short --> (shortcuts)

      con --> (built-in constants)

    userop --> (user-defined operations)

    phrases --> (defined phrases)"""

    # print all the keys, values in {phrases}
    txt, line_width = ' PHRASES ', 56
    ctr1 = math.floor((line_width - len(txt)) / 2)
    ctr2 = math.ceil((line_width - len(txt)) / 2)
    window.addstr('\n' + '='*ctr1 + txt + '='*ctr2 + '\n')

    window.refresh()

    # Print out only the first 15 phrases. The rest of this dictionary simply provides possible substitute commands that a user might mistakenly type.
    print_info_utility(window, dict(list(phrases.items())[:15]))

    return stack


def print_math_ops(stack, item, window):  # command: math
    """List all math operations.

To get a list of commands, math operations, shortcuts,
constants, user-defined operations, or phrases type:

    com --> (commands)

    math --> (math operations)

    short --> (shortcuts)

      con --> (built-in constants)

    userop --> (user-defined operations)

    phrases --> (defined phrases)"""

    # print all the keys, values in {op1} and {op2}
    txt, line_width = ' MATH OPERATIONS ', 56
    ctr1 = math.floor((line_width - len(txt)) / 2)
    ctr2 = math.ceil((line_width - len(txt)) / 2)
    window.addstr('\n' + '='*ctr1 + txt + '='*ctr2 + '\n')

    window.refresh()

    # "op1" and "op2" need to be combined, because both contain math operations.
    all_math_ops = {**op2, **op1}

    print_info_utility(window, all_math_ops)

    return stack


def print_shortcuts(stack, item, window):  # command: short
    """List shortcuts to frequently used math operations and
other commands.

To get a list of commands, math operations, shortcuts,
constants, user-defined operations, or phrases type:

    com --> (commands)

    math --> (math operations)

    short --> (shortcuts)

      con --> (built-in constants)

    userop --> (user-defined operations)

    phrases --> (defined phrases)"""

    # print all the keys, values in {shortcuts}
    txt, line_width = ' SHORTCUTS ', 56
    ctr1 = math.floor((line_width - len(txt)) / 2)
    ctr2 = math.ceil((line_width - len(txt)) / 2)
    window.addstr('\n' + '='*ctr1 + txt + '='*ctr2 + '\n')

    window.refresh()

    print_info_utility(window, shortcuts)

    return stack


def print_constants(stack, item, window):  # command: con
    """List constants and conversions.

Note: This list does not include user-defined constants.
That list is accessed by typing:

    userop

To get a list of commands, math operations, shortcuts,
constants, user-defined operations, or phrases type:

    com --> (commands)

    math --> (math operations)

    short --> (shortcuts)

      con --> (built-in constants)

    userop --> (user-defined operations)

    phrases --> (defined phrases)"""

    # print all the keys, values in {constants}
    txt, line_width = ' CONSTANTS & UNCOMMON CONVERSIONS ', 56
    ctr1 = math.floor((line_width - len(txt)) / 2)
    ctr2 = math.ceil((line_width - len(txt)) / 2)
    window.addstr('\n' + '='*ctr1 + txt + '='*ctr2 + '\n')

    print_info_utility(window, constants)

    return stack


def print_dict(stack, item, window):  # command: userop
    """List user-defined operations.

To use a user-defined operation, type its name. Either
the constant's value will be placed on the stack or
the operation will be executed.

NOTE: User-defined operation names must be typed on
their own command line since, by design, they replace
whatever is on the current command line. In other
words, they ARE a whole command line in themselves.

Related commands:

         user --> create, edit, save user-defined
                  constants and operations

    userhelp --> details on how to create a
                  user-defined operation"""

    # print all the keys, values in {user_dict}
    try:
        with open("constants.json", 'r') as file:
            user_dict = json.load(file)
    except FileNotFoundError:
        user_dict = {}

    txt, line_width = ' USER-DEFINED OPERATIONS ', 56
    ctr1 = math.floor((line_width - len(txt)) / 2)
    ctr2 = math.ceil((line_width - len(txt)) / 2)
    window.addstr('\n' + '='*ctr1 + txt + '='*ctr2 + '\n')

    for k, v in user_dict.items():
        # String together k and v[1] to it is no longer than 56
        i = k + ': ' + str(v[0]) + ' -- '
        j = str(v[1])
        j = j[0:(56 - len(i))]
        window.addstr(i + j + '\n')

    window.addstr('='*line_width + '\n')
    window.addstr('\n\n')
    window.addstr("Press <ENTER> to continue...")
    window.refresh()

    current_row, current_col = get_current_yx(window)
    input = get_user_input(window, current_row, current_col, '')

    return stack


def print_info_utility(window, dict):
    """
    Utility to print the contents of {commands}, {op1}, etc. so user can get quick information about any of those commands, operations, etc.

    Args:
        window ([curses.window]): [this terminal window]
        dict ([dict]): [any dictionary that gets pass in]
    """
    max_terminal_rows, max_terminal_cols = get_terminal_dims(window)
    current_row, current_col = get_current_yx(window)

    row_num, line_width = 10, 56
    for k, v in dict.items():
        row_num += 1
        if row_num == max_terminal_rows - 4:
            r, c = max_terminal_rows - 4, 29
            window.addstr('\n')
            input = get_user_input(window, None, None, "Press <ENTER> to continue...")
            window.move(9, 0)
            window.clrtobot()
            window.move(9, 0)
            window.refresh()
            row_num = 9

        # NOTE: {Phrases} contains long strings, so we have to display this dictionary differently.
        if "decimal to binary" in dict.keys():
            txt = '{:>25}'.format(k) + '|' + v[1] + '\n'
        else:
            txt = '{:>13}'.format(k) + '|' + v[1] + '\n'
        window.addstr(txt)
        window.refresh()

    window.addstr('='*line_width + '\n\n')
    window.refresh()

    input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    return None


# ==== CALCULATOR SETTINGS =============================

def calculator_settings(stack, settings, window):  # command: set
    """Access and edit calculator settings. You can:

   (1) Change the number of decimals that display in
       the stack.

   (2) Turn the thousands separator on or off.

   (3) Determine number format (normal/scientific)"""

    # retrieve settings from config.json
    try:
        with open("config.json", 'r') as file:
            settings = json.load(file)
    except FileNotFoundError:
        # save default settings to config.json:
        settings = {
            'dec_point': '4',
            'separator': ',',
            'notation': 'normal'
        }
        with open('config.json', 'w+') as file:
            file.write(json.dumps(settings, ensure_ascii=False))

    while True:
        window.move(8, 0)
        window.clrtobot()
        # Print the current settings
        window.addstr('\n' + '='*13 + ' CURRENT SETTINGS ' + '='*13 + '\n')
        for k, v in settings.items():
            if k == "dec_point":
                window.addstr('Decimal points (0-28): ' + v + '\n')
            elif k == 'separator':
                if settings['separator'] == '':
                    window.addstr('            Separator: ' + 'none' + '\n')
                else:
                    window.addstr('            Separator: ' + ',' + '\n')
            elif k == 'notation':
                if settings['notation'] == 'normal':
                    window.addstr('             Notation: ' + 'normal' + '\n')
                else:
                    window.addstr('             Notation: ' + 'scientific' + '\n')
            else:
                pass
        window.addstr('='*45 + '\n')
        window.refresh()

        # Print a menu of setting options.
        window.addstr("\n\n========= CHANGE SETTINGS =========\n")
        window.addstr("\n      Set decimal <p>oint")
        window.addstr("\nSet thousands <s>eparator")
        window.addstr("\n        Number <n>otation")
        window.addstr("\n                   <E>xit\n\n")
        window.addstr('===================================\n\n')
        window.addstr("       <p> <s> <n> or <e>: ")
        window.refresh()

        """
        NOTE:
            The following code listens for instances where the <ENTER> key is pressed when the user has not entered a menu choice. In this case, either the user exits settings or, if the user is in one of the settings options, the user leaves without changing the setting.
        """
        menu_choice = ''
        menu_choice = get_user_input(window, None, None, "")
        menu_choice = menu_choice.lower()
        curses.noecho()

        if not menu_choice or menu_choice not in ['p', 's', 'n', 'e']:
            break

        # Change menu setting
        if menu_choice == 'p':
            while True:
                window.addstr("\nEnter number of decimal points (0-28): ")
                curses.echo()
                m = window.getstr().decode(encoding='utf8')
                curses.noecho()
                window.addstr(m)
                window.refresh()
                if not m:
                    break
                # If this try...except fails, user did not enter an int.
                try:
                    # m has to be 0-28, since floats are only accurate to 18 places.
                    # If m not between 0 and 18, create an error.
                    t = int(m) if (0 <= int(m) <= 28) else int('x')
                    settings['dec_point'] = str(int(t))
                    break
                except:
                    window.addstr('\nEnter an integer between 0 and 28, inclusive.\n')
                    input = get_user_input(window, None, None, '')
                    break

        # change thousands separator setting
        elif menu_choice == 's':
            window.addstr("\nThousands separator ('none' or ','): ")
            curses.echo()
            separator = window.getstr().decode(encoding='utf8')
            curses.noecho()
            window.addstr(separator)
            window.refresh()
            if separator.strip().lower() == 'none':
                settings['separator'] = ''
            elif separator.strip() == ',':
                settings['separator'] = ','
            else:
                pass

        elif menu_choice == 'n':
            window.addstr("\nNumber notation ('<n>ormal' or '<s>cientific'): ")
            curses.echo()
            notation = window.getstr().decode(encoding='utf8')
            curses.noecho()
            window.addstr(notation)
            window.refresh()
            if notation.strip().lower() == 's':
                settings['notation'] = 'scientific'
            elif notation.strip().lower() == 'n':
                settings['notation'] = 'normal'
            else:
                pass
        else:
            pass

        # e or exit to exit out of settings
        if menu_choice == 'e' or menu_choice == 'exit' or menu_choice == 'None' or not menu_choice:
            break

    # save {settings} to file, whether changed or not
    with open('config.json', 'w+') as file:
        file.write(json.dumps(settings, ensure_ascii=False))

    # Print the register, considering the new settings.
    stack = print_register(stack, settings, window)

    return settings


# ==== MATH OPERATIONS from {op1} =================================

def log(stack, item, window):     # command: log
    """Returns the log(10) of the x: value.

Example:

    100 log --> x: 2, since 10^2 = 100."""
    if stack[0] <= 0:
        window.addstr('='*45 + '\n')
        window.addstr('Cannot return log of numbers <= 0.\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")
        return stack
    x = stack[0]
    stack[0] = Decimal(str(math.log10(x)))
    return stack


def ceil(stack, item, window):  # command: ceil
    """Returns to ceiling, the next higher integer, of x:

Example:

    6.3 ceil -> 7"""
    x = stack[0]
    stack[0] = Decimal(str(math.ceil(x)))
    return stack


def floor(stack, item, window):  # command: floor
    """Returns the floor, the next lower integer, of x:

Example:

    6.9 floor -> 6"""
    x = stack[0]
    stack[0] = Decimal(str(math.floor(x)))
    return stack


def factorial(stack, item, window):  # command: !
    """x: factorial

Example (1):

    4 ! --> x: 24"""
    if stack[0] < 0:
        window.addstr('='*45 + '\n')
        window.addstr('Factorial not defined for negative numbers.\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")
        return stack
    x = int(stack[0])
    stack[0] = Decimal(str(math.factorial(x)))
    return stack


def negate(stack, item, window):  # command: n
    """Negative of x:

Example:

    4 n --> x: -4"""
    x = stack[0]
    stack[0] = Decimal(str(operator.neg(x)))
    return stack


def sin(stack, item, window):     # command: sin
    """sin(x) -- x: must be radians."""
    x = stack[0]
    stack[0] = Decimal(str(math.sin(x)))
    return stack


def cos(stack, item, window):  # command: cos
    """cos(x) -- x: must be radians."""
    x = stack[0]
    stack[0] = Decimal(str(math.cos(x)))
    return stack


def tan(stack, item, window):     # command: tan
    """tan(x) -- x: must be radians."""
    x = stack[0]
    stack[0] = Decimal(str(math.tan(x)))
    return stack


def asin(stack, item, window):    # command: asin
    """asin(x) -- x: must be radians."""
    x = stack[0]
    stack[0] = Decimal(str(math.asin(x)))
    return stack


def acos(stack, item, window):    # command: acos
    """acos(x) -- x: must be radians."""
    x = stack[0]
    stack[0] = Decimal(str(math.acos(x)))
    return stack


def atan(stack, item, window):    # command: atan
    """atan(x) -- x: must be radians."""
    x = stack[0]
    stack[0] = Decimal(str(math.atan(x)))
    return stack


def pi_value(stack, item, window):  # command: pi
    """Puts the value of pi on the stack."""
    stack.insert(0, Decimal(str(math.pi)))
    return stack


def deg(stack, item, window):     # command: deg
    """Convert x: value from radians to degrees."""
    stack[0] = Decimal(str(math.degrees(stack[0])))
    return stack


def rad(stack, item, window):     # command: rad
    """Convert x: value from degrees to radians."""
    stack[0] = Decimal(str(math.radians(stack[0])))
    return stack


def absolute(stack, item, window):  # command: abs
    """Put the absolute value of x: on the stack."""
    x = stack[0]
    stack[0] = Decimal(str(abs(x)))
    return stack


def random_number(stack, item, window):  # command: rand
    """Generate a random integer between y (exclusive) and
    x (inclusive).

Example:

    1 100 rand --> x: 43 (random number between 1
        (exclusive) and 100 (inclusive))"""
    # make sure x: and y: are in correct order
    x, y = int(stack[0]), int(stack[1])
    if x == y:
        window.addstr('='*45 + '\n')
        window.addstr('Must have a range of numbers.\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")
        return stack
    if y > x:
        x, y = y, x
    ri = random.randint(y, x)
    stack.insert(0, Decimal(str(ri)))
    return stack


def add(stack, item, window):     # command: +
    """y: + x:

Example:
    4 3 + --> x: 7"""
    x, y = stack[0], stack[1]
    stack.pop(0)
    stack.pop(0)
    stack.insert(0, x + y)
    return stack


def sub(stack, item, window):     # command: -
    """y: - x:

Example:

    4 3 - --> x: 1"""
    x, y = stack[0], stack[1]
    stack.pop(0)
    stack.pop(0)
    stack.insert(0, y - x)
    return stack


def mul(stack, item, window):  # command: * or x
    """y: times x:

Example:

    5 3 * --> x: 15"""
    x, y = stack[0], stack[1]
    stack.pop(0)
    stack.pop(0)
    stack.insert(0, y * x)
    return stack


def truediv(stack, item, window):  # command: /
    """y: divided by x:

Example:

    12 3 / --> x: 4

Note: division by zero will generate an error."""
    x, y = stack[0], stack[1]
    stack.pop(0)
    stack.pop(0)
    stack.insert(0, y / x)
    return stack


def mod(stack, item, window):  # command: %
    """
Modulo: remainder after dividing one number by another.

Example (1):
    5 2 % --> x: 1

Example (2):
    4 2 % --> x: 0

Note: A useful fact is that only even numbers will
result in a modulo of zero when divided by 2."""
    x, y = stack[0], stack[1]
    stack.pop(0)
    stack.pop(0)
    stack.insert(0, y % x)
    return stack


def power(stack, item, window):      # command: ^
    """y: to the power of x:

Example:

    10 2 ^ --> x: 100

NOTE: In python, "**" is used for exponents, where
2 ** 3 yields 8. However, ada can't distinguish "**"
from "* *" since both of these appear to be two
multiplication symbols in a row. For this reason, use
"^", instead of "**" for power operations."""
    x, y = stack[0], stack[1]
    stack.pop(0)
    stack.pop(0)
    try:
        stack.insert(0, y ** x)
    except Exception as error:
        window.addstr('\n' + '='*45 + '\n')
        window.addstr("Cannot find root of a negative number.")
        window.addstr('\n' + '='*45 + '\n\n')
        window.refresh()
        input = get_user_input(window, None, None, "Press <ENTER> to continue...")
    return stack


def math_op1(stack, item, window):
    """
    Math operations described in the {op1} dictionary.
    """
    operation = op1[item][0]
    try:
        stack = operation(stack, item, window)
    except:
        stack = operation(stack, item, window)
    return stack

# ==== MATH OPERATIONS from {op2} ============================================


def math_op2(stack, item, window):
    """Add, subtract, multiply, divide, modulus, power."""
    if item == '/' and stack[0] == 0:
        window.addstr('='*45 + '\n')
        window.addstr('Cannot divide by zero.\n')
        window.addstr('='*45 + '\n\n')
        window.refresh()
        input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    else:
        operation = op2[item][0]
        stack = operation(stack, item, window)
    return stack


# ==== NUMBER SYSTEM CONVERSIONS =============================

def convert_bin_to_dec(stack, window, bin_value):  # command: bindec
    """Convert a binary value to decimal. Replaces the value
in x: with the decimal value.

TIP: As a shortcut, it is not necessary to issue the
     the command: "bindec". Entering a binary number
     beginning with '0b' is sufficient.

Example:

    0b1000 --> x: 8"""

    # -- RPN() handles this directly without going to process_item()
    # -- entering '0b' is sufficient to convert binary to decimal
    # -- so entering 'bindec' actually does nothing

    # If user tries to convert a string that does not start with "0b...", then window is passed in as a string, not a "curses" object. In this case, no error message can be printed, since no "window" exists.
    if isinstance(window, str):
        return stack

    try:
        stack.insert(0, Decimal(str(int(bin_value, 2))))
    except:
        window.addstr('\n\n' + '='*45 + '\n')
        window.addstr('Not a valid binary value.\nExample: 0b1000\n')
        window.addstr('='*45 + '\n\n')
        window.refresh()
        input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    return stack


def convert_dec_to_bin(stack, item, window):  # command: decbin
    """Convert x: from decimal to binary. Binary value is a
string so it is reported as a string, and not placed on
the stack.

Example:

    8 decbin --> "0b1000"

Note: The x: value remains on the stack.
      The binary value is shown as a string."""
    window.addstr('\n' + '='*45 + '\n')
    window.addstr(bin(int(stack[0])) + '\n')
    window.addstr('='*45 + '\n\n')
    window.refresh()

    input = get_user_input(window, None, None, "Press <ENTER> to continue...")
    return stack


def convert_dec_to_hex(stack, item, window):  # command: dechex
    """Convert x: from decimal to hexadecimal. The resulting
hexadecimal number is a string, so it is reported as a
string, and not placed on the stack.

Note: The x: value remains on the stack.
      The hex value is shown as a string."""

    # SOURCE:
    # https://owlcation.com/stem/Convert-Hex-to-Decimal
    hex_dict = {
        '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5',
        '6': '6', '7': '7', '8': '8', '9': '9', '10': 'A',
        '11': 'B', '12': 'C', '13': 'D', '14': 'E', '15': 'F'
    }
    result = 1
    hex_value = ''
    cnt = 0
    dec_number = stack[0]
    while True:
        stack[0] = stack[0] / Decimal('16')
        stack = split_number(stack, item, window)
        result = int(stack[0] * 16)
        if stack[0] == 0 and stack[1] == 0:
            break
        result = hex_dict[str(result)]
        hex_value += result
        stack.pop(0)
        cnt += 1

    # A decimal value of zero, won't be caught by the while loop, so...
    if cnt == 0:
        hex_value = '0'
    hex_value = '0x' + hex_value[::-1]
    stack[0] = dec_number

    window.addstr('\n' + '='*45 + '\n')
    window.addstr(hex_value + '\n')
    window.addstr('='*45 + '\n\n')
    window.refresh()

    input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    return stack


def convert_hex_to_dec(stack, window, hex_value='not_hex'):  # command: hexdec
    """Convert a hexadecimal (string beginning with "0x") to
decimal. Since the hexadecimal number is a string, it
is not placed on the stack.

It is not necessary to issue a command. Entering a hex
number beginning with '0x' is sufficient.

Example:
    0xA --> x: 10"""

    # -- RPN() handles this directly without going to process_item().Entering '0x' is sufficient to convert hex to decimal, so entering 'hexdec' actually does nothing

    # If there is not hex value, then just return
    if isinstance(window, str):
        return stack

    # SOURCE:
    # https://owlcation.com/stem/Convert-Hex-to-Decimal
    if hex_value == 'not_hex':
        window.addstr('\n\n' + '='*45 + '\n')
        window.addstr('Enter hex values preceded with "0x".\n')
        window.addstr('='*45 + '\n\n')

        window.refresh()
        input = get_user_input(window, None, None, "Press <ENTER> to continue...")
        return stack
    else:
        hex_dict = {
            '0': '0', '1': '1', '2': '2', '3': '3', '4': '4', '5': '5',
            '6': '6', '7': '7', '8': '8', '9': '9', '10': 'A',
            '11': 'B', '12': 'C', '13': 'D', '14': 'E', '15': 'F'
        }
        hex_value = hex_value[::-1].upper()
        result = 0
        try:
            for ndx, i in enumerate(hex_value):
                n = [k for k, v in hex_dict.items() if v == i]
                result += (int(n[0]) * math.pow(16, ndx))
            stack.insert(0, Decimal(str(result)))
        except IndexError:
            window.addstr('\n\n' + '='*45 + '\n')
            window.addstr('Not a valid hex value.\n')
            window.addstr('='*45 + '\n')
            window.refresh()
            input = get_user_input(window, None, None, "Press <ENTER> to continue...")
        return stack

# ==== USER-DEFINED OPERATIONS =============================


def user_defined(stack, user_dict, window):  # command: user
    """Define, edit, or delete a user-defined operation or
constant.

    Related commands:

          userop --> list the currently defined
                      operations

        userhelp --> help on how to create
                     user-defined operations"""

    try:
        with open("constants.json", 'r') as file:
            user_dict = json.load(file)
    except:
        user_dict = {}

    name, value, description = '', '', ''

    break_loop = False
    while True:

        current_row, current_col = get_current_yx(window)
        window.move(current_row-1, 0)
        window.clrtoeol()

        window.addstr('\n')
        window.addstr(' NAME: lowercase; enter a current name to delete\n       or redefine.\n')
        window.addstr('VALUE: Enter either a number or an operation.\n\n')
        window.addstr('If you need information on operations,\npress <ENTER> then:\n\n     userhelp\n\n\n')
        window.refresh()
        name = get_user_input(window, None, None, "Name of operation/constant: ")

        # if no name was entered, leave this function
        if not name:
            break

        # check to see if there are any uppercase letters: ada can't handle them.
        upper = False
        for i in range(len(name)):
            if name[i] in ascii_uppercase:
                s = input('Cannot use uppercase letters in a name.\nPress <enter> to continue...')
                upper = True
                break
        if upper:
            continue

        # if the constant already exists, edit or delete it
        if name in user_dict.keys():
            window.addstr("\nEnter new value to redefine " + name + ".\n")
            window.addstr('Enter no value to delete ' + name + ".\n")
        # make sure name is not a "system" name
        elif name in op1.keys() or \
                name in op2.keys() or \
                name in constants.keys() or \
                name in commands.keys() or \
                name in shortcuts.keys() or \
                name in alpha.keys() or \
                name in phrases.keys():
            window.addstr('\n' + '='*45 + '\nName already in use. Choose another.\n' + '='*45 + '\n')
            continue

        # if you entered a name, get a value
        if name:
            value = get_user_input(window, None, None, '\nValue or operation: ')
            if value != '':
                try:
                    value = str(value)
                except:
                    value = value.strip()
                    # if user put commas in a number, strip them
                    try:
                        value = value.replace(',', '')
                    except ValueError:
                        pass

        # if you enter no name and no value, then exit...
        if not name and value == '':
            break

        # if you gave a name, but enter no value, then offer to delete name
        if name:
            if name in user_dict.keys() and value == '':
                ok_delete = get_user_input(window, None, None, 'Delete ' + name + '? (Y/N) ')
                if ok_delete.upper() == 'Y':
                    del user_dict[name]

            elif (not name in user_dict.keys()) and value == '':
                txt = '\nWhen you enter no value, it is presumed you want\nto delete the name "' + \
                    name + '". However, no such name\nexists. Press <ENTER> to continue...'
                s = get_user_input(window, None, None, txt)
            else:
                pass

        # if you entered a name and a value, get a description
        if name and value != '':
            description = get_user_input(window, None, None, "\nDescription (optional): ")

        # if you entered a name and a value (description is optional), update {user_dict}
        if name and value != '':
            user_dict.update({name: (value, description)})

        if not name and value == '':
            break_loop = True

        repeat = ''
        while repeat.upper() not in ['Y', 'N']:
            repeat = get_user_input(window, None, None, "\nAdd or edit another constant? (Y/N): ")
        if repeat.upper() == 'N':
            break_loop = True

        with open('constants.json', 'w+') as file:
            file.write(json.dumps(user_dict, ensure_ascii=False))

        window.move(8, 0)
        window.clrtobot()
        window.move(9, 0)

        item = None
        print_dict(stack, item, window)

        if break_loop:
            break

    return stack, user_dict


# ==== STACK FUNCTIONS =============================

def clear(stack, item, window):  # command: clear or c
    """Clear all elements from the stack. The shortcut c can
also be used.

To be distinguished from:

    trim

that removes all but the x:, y:, z:, and t:
registers."""

    stack = [Decimal('0.0'), Decimal('0.0'), Decimal('0.0'), Decimal('0.0')]
    return stack


def drop(stack, item, window):  # command: drop or d
    """Drop the last element off the stack. This operation is
very useful when you put a value on the stack that is
a mistake. In combination with either ru (rollup),
rd (rolldown) or s (swap), you can manipulate the
contents of the stack without having to c (clear) and
retype.

Example:

    4 3 drop --> x: 4
    or
    4 3 d --> x: 4"""
    stack = stack[1:]
    return stack


def dup(stack, item, window):  # command: dup or <ENTER>
    """Duplicate the value in the x: register. <ENTER> with
nothing else on the command line will also duplicate x.

Examples (1):

    4 dup --> x: 4  y: 4

Example (2):

    4 <enter> <enter> --> y: 4  x: 4"""
    x = stack[0]
    stack.insert(0, x)
    return stack


def get_lastx(stack, lastx_list, window=None):  # command: lastx
    """Put the last x: value on the stack.

Examples:
    4 5 ^ --> x: 1024

    lastx --> y: 1024  x: 5

    3 4 --> y: 3  x: 4
    lastx --> x: 4 (duplicates x:)"""
    stack.insert(0, Decimal(str(lastx_list[-2])))
    return stack


def list_stack(stack, item, window):  # command: list
    """Display the contents of the entire stack."""
    stack_names = [' x', ' y', ' z', ' t']
    window.addstr('\n')

    # stack must always have at least 4 elements
    while len(stack) < 4:
        stack.insert(len(stack), Decimal('0.0'))

    # add blank stack_names, as needed
    r = '  '
    for i in range(len(stack) - 4):
        stack_names.append(r)

    window.addstr('='*15 + ' CURRENT STACK ' + '='*15 + '\n')
    for register in range(len(stack)-1, -1, -1):
        # get the number of decimals from {settings}
        dp = settings['dec_point']

        if (stack[register] > 1e9 or stack[register] < (-1 * 1e8)) and (stack[register] != 0.0):
            # switch to scientific notation
            fs = ('{:.0' + dp + 'e}').format(stack[register])
        else:
            # switch to regular number notation
            fs = ('{:.0' + dp + 'f}').format(stack[register])

        # line up decimal points
        p = 11 + len(fs) - fs.find('.')

        window.addstr(stack_names[register] + ':' + ('{:>' + str(p) + '}').format(fs) + '\n')

    window.addstr('='*45 + '\n\n')
    window.refresh()

    input = get_user_input(window, None, None, "\nPress <ENTER> to continue...")

    return stack


def print_tape(window, stack, entered_list, lastx_list, user_dict, mem, settings, tape):  # command: tape
    """Display the tape (a running record of all operations)
from the current session. By selecting a specific line
in the tape, the user can re-run a particular operation.
The tape is not saved between sessions."""

    if tape:
        tape = tape[0:-1] if tape[-1] == 'tape' else tape
    window.addstr('\n' + '='*19 + ' TAPE ' + '='*20 + '\n')

    # Print each of the items store in [tape] in the terminal.
    ndx = 0
    while True:
        try:
            command_line = ''
            for i in tape[ndx]:
                command_line += str(i) + " "
            window.addstr(str(ndx+1) + ". " + command_line + '\n')
            window.refresh()
            ndx += 1
            if ndx >= len(tape):
                break
        except IndexError:
            break

    window.addstr('='*45 + '\n\n')
    window.refresh()

    input = get_user_input(window, None, None, "Press <ENTER> to continue or select a line number...")

    # If the user selects an item number from the tape, clear the screen and show that item in the terminal as if the user entered it.
    if len(input) > 0:
        window.move(8, 0)
        window.clrtobot()
        command_line = ''
        for i in tape[int(input)-1]:
            command_line += str(i) + " "
        window.refresh()

        # Copy the command to the system clipboard and provide instruction to user on how to execute the command, if they so wish.
        pc.copy(command_line)
        waiter = get_user_input(window, None, None, "\nPress <ENTER> then CTRL-v to paste\nyour selection to the command line...")

    return tape


def roll_up(stack, item, window):  # command: rollup or ru
    """rollup (shortcut ru) rolls the stack up.

x:-->y:, y:-->z:, z:-->t:, and t: wraps around to
become x:."""
    x, y, z, t = stack[0], stack[1], stack[2], stack[3]
    stack[0], stack[1], stack[2], stack[3] = t, x, y, z

    return stack


def roll_down(stack, item, window):  # command: rolldown or rd
    """rolldown (shortcut rd) rolls the stack down.

t:-->z:, z:-->y:, y:-->x:, and x: wraps around to
become t:."""
    x, y, z, t = stack[0], stack[1], stack[2], stack[3]
    stack[0], stack[1], stack[2], stack[3] = y, z, t, x
    return stack


def round_y(stack, item, window):  # command: round or r
    """Round y: by x:.

Example

    3.1416 2 round --> x: 3.14

You can also use a shortcut for this operation:
    3.1416 2 r --> x: 3.14"""
    x, y = int(stack[0]), stack[1]
    if x < 0:
        window.addstr('\n' + '='*45)
        window.addstr('\nCannot round by a negative number.\n')
        window.addstr('='*45)
        window.refresh()
        input = get_user_input(window, None, None, "\n")
    else:
        stack.pop(0)
        stack[0] = Decimal(str(round(y, x)))
    return stack


def split_number(stack, item, window):  # command: split
    """Splits x: into integer and decimal parts, leaving the
original value on the stack.

Example:
    3.1416 split --> z: 3.1416  y: 3  x: 0.1416"""
    n = stack[0]
    n_int = int(n)
    n_dec = n - n_int
    stack.insert(0, Decimal(str(n_int)))
    stack.insert(0, Decimal(str(n_dec)))
    return stack


def sqrt(stack, item, window):    # command: sqrt
    """Find the square root of x:.

Example:
    25 sqrt --> x: 5"""
    x = stack[0]
    if x >= 0:
        stack.pop(0)
        stack.insert(0, Decimal(str(math.sqrt(x))))
    else:
        window.addstr('='*45 + '\n')
        window.addstr('Square root of a negative number is undefined.\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")
    return stack


def stats(stack, settings, window):     # command: stats
    """Summary stats for stack.

Note: This function is non-destructive: the stack is
left intact.

Results include:
-- Count
-- Mean
-- Median
-- Standard deviation
-- Minimum
-- Maximum
-- Sum
The question of what is included can be addressed best
by example:

0.0000
0.0000
0.0000
0.0000
100.0000
0.0000
2.0000
3.0000

============ SUMMARY STATISTICS =============
        Count:4.0000
         Mean:26.2500
       Median:2.5000
      Std Dev:49.1825
      Minimum:0.0000
      Maximum:100.0000
          Sum:105.0000
=============================================

The -0- between 100 and 2 is included, but the zeroes
"above" 100 are not. The program starts at the "top"
of the stack and discards each zero until it gets to a
non-zero number."""

    # strip out all the zero values at the beginning of a copy of [stack]
    stack_copy = stack.copy()
    for i in range(len(stack_copy)-1, 0, -1):
        if stack_copy[i] == 0:
            stack_copy.pop(i)
        else:
            break
    window.addstr('\n')

    # get the stats: count, mean, median, min, max, sum; save sd for later
    cnt = len(stack_copy)
    mn = sum(stack_copy)/len(stack_copy)
    md = statistics.median(stack_copy)
    minimum = min(stack_copy)
    maximum = max(stack_copy)
    sm = sum(stack_copy)

    fs = '{:.' + settings['dec_point'] + 'f}'
    window.addstr('='*12 + ' SUMMARY STATISTICS ' + '='*13 + '\n')
    window.addstr('        Count:' + fs.format(cnt) + '\n')
    window.addstr('         Mean:' + fs.format(mn) + '\n')
    window.addstr('       Median:' + fs.format(md) + '\n')

    err = ''  # required if there's a statistics error
    # get standard deviation + catching potential error
    try:
        sd = statistics.stdev(stack_copy)
        window.addstr('      Std Dev:' + fs.format(sd) + '\n')

    except statistics.StatisticsError:
        sd = ''
        err = "Standard deviation requires at least two non-zero data points."
        window.addstr('      Std Dev: not computed\n')

    window.addstr('      Minimum:' + fs.format(minimum) + '\n')
    window.addstr('      Maximum:' + fs.format(maximum) + '\n')
    window.addstr('          Sum:' + fs.format(sm) + '\n')
    if err:
        window.addstr('\n' + err + '\n\n')

    window.addstr('='*45 + '\n')
    window.addstr("Zero values 'above' the first (top) non-zero element in\nthe stack were ignored. Use <list> to inspect stack." + '\n\n')
    window.refresh()
    input = get_user_input(window, None, None, "Press <ENTER> to continue...")
    return stack


def swap(stack, item, window):    # command: swap or s
    """Swap x: and y: values on the stack.

Example (1):
    y: 3  x: 4 swap --> y: 4  x: 3

Example (2):
    y: 4  x: 3 s --> y: 3  x: 4

Note that example (2) uses a shortcut. To list
shortcuts, type:

    short"""
    stack[0], stack[1] = stack[1], stack[0]
    return stack


def trim_stack(stack, item, window):  # command: trim
    """Remove all elements on the stack except
x:, y:, z:, t:.

Note: You can use

    list

to inspect the entire stack."""
    stack = stack[0:4]
    return stack


# ==== COLOR FUNCTIONS =============================

def hex_to_rgb(stack, item=None, window=None):  # command: rgb or enter "#..."
    """Convert hex color to rgb.

Example:
    # b31b1b rgb --> z: 179  y: 27  x: 27
    or
    # b31b1b --> z: 179  y: 27  x: 27

NOTE 1: To detect a hex value, the string you enter
must begin with "#" (without the quotes).

NOTE 2: Entering "#" and <ENTER> is sufficient to
convert a hex color to rgb. Issuing the "rgb"
command works, but if ada detects the "#" character,
conversion to rgb is assumed automatically."""

    try:
        if item[0] == '#':
            item = item[1:]
            try:
                r, g, b = int(item[0:2], 16), int(item[2:4], 16), int(item[4:6], 16)
            except ValueError:
                window.addstr('\n\n' + '='*45 + '\n')
                window.addstr('Not a valid hex color.\n')
                window.addstr('='*45 + '\n')
                window.refresh()
                input = get_user_input(window, None, None, "Press <ENTER> to continue...")
                return stack

            stack.insert(0, Decimal(str(r)))
            stack.insert(0, Decimal(str(g)))
            stack.insert(0, Decimal(str(b)))
        else:
            window.addstr('\n\n' + '='*45 + '\n')
            window.addstr('You must provide a hex value.\nExample: #b31b1b\n')
            window.addstr('='*45 + '\n')
            window.refresh()
            input = get_user_input(window, None, None, "Press <ENTER> to continue...")
    except:
        pass
    return stack


def rgb_to_hex(stack, item, window):  # command: hex
    """Convert rgb color (z:, y:, x:) to hex color.

Example:
    179 27 27 hex --> #b31b1b

Since the result is a string, the stack is unmodified."""
    r, g, b = int(stack[2]), int(stack[1]), int(stack[0])
    c = list(range(0, 256))
    if r in c and g in c and b in c:
        window.addstr('\n\n' + '='*45 + '\n')
        window.addstr('#' + str(hex(r)[2:]) + str(hex(g)[2:]) + str(hex(b)[2:]) + '\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "Press <ENTER> to continue...")
    else:
        window.addstr('\n\n' + '='*45 + '\n')
        window.addstr('r, g, or b not in the\nrange of 0 to 255.\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "Press <ENTER> to continue...")
    return stack


def get_hex_alpha(stack, item, window):  # command: alpha
    """Put a percent alpha value (between 0 and 100) in x:

This operation returns the hex equivalent, reported as
a string.

Example:
    75 alpha --> BF"""
    if stack[0] >= 0 and stack[0] <= 100:
        n = str(int(stack[0]))
        window.addstr('\n' + '='*45 + '\n')
        window.addstr('alpha: ' + alpha[n] + '\n')
        window.addstr('='*45 + '\n\n')
    else:
        window.addstr('\n' + '='*45 + '\n')
        window.addstr("Alpha value must be between 0 and 100." + '\n')
        window.addstr('='*45 + '\n\n')

    window.refresh()

    input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    return stack


def list_alpha(stack, item, window):  # command: list_alpha
    """List alpha values and their hex equivalents."""

    max_rows, max_cols = get_terminal_dims(window)
    current_row, current_col = get_current_yx(window)

    window.addstr('\n' + '='*15 + ' ALPHA VALUES ' + '='*16 + '\n')
    row_num = 9
    for k, v in alpha.items():
        window.addstr('{:>3}'.format(k) + ": " + v + '\n')
        row_num += 1
        if row_num >= max_rows-5:
            window.refresh()
            input = get_user_input(window, None, None, "Press <ENTER> to continue...")
            window.move(8, 0)
            window.clrtobot()
            window.move(9, 0)
            row_num = 9

    window.addstr('='*45 + '\n\n')
    window.refresh()

    input = get_user_input(window, None, None, "Press <ENTER> to continue...")
    return stack


# ==== COMMON CONVERSIONS =============================

def ci(stack, item, window):
    """Convert cm to inches.\n\nExample:

2.54 inch --> x: 1 (converts 2.54 cm to 1 inch)"""
    # 1 in = 2.54 cm
    stack[0] = stack[0] / Decimal(str(2.54))
    return stack


def ic(stack, item, window):
    """Convert inches to cm.\n\nExample:

1.00 cm --> 2.54 (converts 1 inch to 2.54 cm)"""
    # 1 in = 2.54 cm
    stack[0] = stack[0] * Decimal(2.54)
    return stack


def lengths(stack, item, window):  # command: i
    """
Convert a decimal measurement to a fraction. For
example, you can easily determine what is the
equivalent measure of 2.25 inches in eighths. Very
handy for woodworking.

Example (1)
    2.25 8 i

        t:          2.2500
        z:          2.0000
        y:          2.0000
        x:          8.0000

Translation:
    2.25" equals 2 and 2/8"

============================================

Example (2)
    3.65 32 i

        t:          3.6500
        z:          3.0000
        y:         20.8000
        x:         32.0000

    3.65" equals 3 20.8/32"

============================================

Example (3)
    3.25 64i

        t:          3.2500
        z:          3.0000
        y:         16.0000
        x:         64.0000

    3.25" equals 3 16/64" """

    # Convert a decimal measurement to 1/8", 1/16", 1/32", or 1/64"
    # Enter: X.XX >> 8, 16, 32, or 64 >> i

    if stack[0] == 0:
        window.addstr('='*45 + '\n')
        window.addstr('Enter: 3.25 then 8i\nReturns: z,y,z... 3.25 3 2 8 meaning 3.25" =  3 2/8"\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")
    else:
        n = stack[1]
        n_int = int(stack[1])
        decimal = Decimal(str(n - n_int))
        inches = stack[0]
        stack.pop(0)
        stack.insert(0, Decimal(str(n_int)))
        stack.insert(0, Decimal(str(decimal * inches)))
        stack.insert(0, Decimal(str(inches)))

    return stack


def ftoc(stack, item, window):   # command: fc
    """Convert temperature from F to C.

Example:

    212 fc --> 100 (degrees Centigrade)"""
    # e.g.: enter 32 ftco and return 0
    # C = (5/9)*(°F-32)
    result = Decimal('5') / Decimal('9') * (stack[0] - Decimal('32'))
    stack.pop(0)
    stack.insert(0, Decimal(str(round(result, 1))))

    return stack


def ctof(stack, item, window):  # command: cf
    """Convert temperature from C to F.

Example:

    100 cf --> 212 (degrees Fahrenheit)"""
    # e.g.: enter 0C ctof and return 32F
    # F = (9/5)*(°C)+32
    result = ((Decimal('9') / Decimal('5')) * stack[0]) + Decimal('32.0')
    stack.pop(0)
    stack.insert(0, Decimal(str(round(result, 1))))
    return stack


def go(stack, item, window):    # command go
    """Convert weight from grams to ounces.

Example:

    453.5924 go --> 16 (ounces)"""
    # e.g.: enter 16g and return 453.59237
    stack[0] = stack[0] * Decimal('16.0') / Decimal('453.59237')
    return stack


def og(stack, item, window):    # command og
    """Convert weight from ounces to grams.

Example:

    16 og --> 453.5924 (grams)"""
    # e.g.: enter 16g and return 453.59237
    stack[0] = stack[0] * Decimal('453.59237') / Decimal('16.0')
    return stack


def kp(stack, item, window):    # command kp
    """Convert kilograms to pounds.

Example:

    1 kp --> 2.204_622_621_8 (pounds)"""
    # e.g: enter 1 kp and return 2.2046
    stack[0] = stack[0] * Decimal('2.204_622_621_8')
    return stack


def pk(stack, item, window):    # command pk
    """Convert pounds to kilograms.

Example:

    1 pk --> 2.204_622_621_8 (kilograms)"""
    # e.g: enter 1 pound and return 0.4536
    stack[0] = stack[0] / Decimal('2.204_622_621_8')
    return stack


def km(stack, item, window):    # command km
    """Convert kilometers to miles.

Example:

    1 km --> 0.621_371_192_24 (miles)"""
    # e.g: enter 1 kilometer and return 0.6214
    stack[0] = stack[0] * Decimal('0.621_371_192_24')
    return stack


def mk(stack, item, window):    # command mk
    """Convert miles to kilometers.

Example:

    1 mk --> 1.609344 (kilometer)"""
    # e.g: enter 1 mile and return 1.6093
    stack[0] = stack[0] / Decimal('0.621_371_192_24')
    return stack


def cm(stack, item, window):    # command cm
    """Convert cm H2O to mmHg.

Example:

    5 cm --> 3.6778 (mmHg))"""
    stack[0] = stack[0] / Decimal('1.3595100263597')
    return stack


def mc(stack, item, window):    # command mc
    """Convert mmHg to 6.7976 cm H2O.

Example:

    5 mc --> 6.7976 (cm H2O)"""
    stack[0] = stack[0] * Decimal('1.3595100263597')
    return stack


# ==== MEMORY REGISTER FUNCTIONS =============================

def mem_add(stack, mem, window):  # command: M+
    """Add x: to the y: memory register.

Example:
    1 453
    M+

adds 453 to the current value of the #1 memory register.
If the register doesn't exist, it will be created.

Type:

    ML

to inspect (list) the memory registers."""
    # memory registers range from 1 to infinity
    if Decimal(stack[1]) == int(stack[1]) and stack[1] > 0:
        register, register_value = stack[1], stack[0]
    else:
        window.addstr('='*45 + '\n')
        window.addstr('Register numbers are positive integers, only.' + '\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")
        return stack, mem

    # if the register already exists, add value to what's there
    if register in mem.keys():
        current_value = mem[register]
        # just in case register holds something other than a number
        try:
            stack.pop(0)
            stack.pop(0)
            mem.update({register: register_value + current_value})
        except:
            window.addstr('No operation conducted.\n')
            window.refresh()
            input = get_user_input(window, None, None, "")
    else:
        try:
            stack.pop(0)
            stack.pop(0)
            mem.update({register: register_value})
        except:
            window.addstr('No operation conducted.' + '\n')
            window.refresh()
            input = get_user_input(window, None, None, "")

    return stack, mem


def mem_sub(stack, mem, window):  # command: M-
    """Subtract x: from the y: memory register.

Example:
    3 12
    M-

Subtracts 12 from the current value of the #3 memory
register. If the register doesn't exist, it will be
created.

Type:

    ML

to inspect (list) the memory registers."""
    # Memory registers range from 1 to some very large number.
    if Decimal(stack[1]) == int(stack[1]):
        register, register_value = stack[1], stack[0]
    else:
        window.addst('='*45 + '\n')
        window.addst('Register numbers are positive integers, only.' + '\n')
        window.addst('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")
        return stack, mem

    # If the register already exists, add value to what's there
    if register in mem.keys():
        current_value = mem[register]
        # just in case register holds something other than a number
        try:
            stack.pop(0)
            stack.pop(0)
            mem.update({register: current_value - register_value})
        except:
            window.addst('No operation conducted.' + '\n')
            window.refresh()
            input = get_user_input(window, None, None, "")
    else:
        try:
            stack.pop(0)
            stack.pop(0)
            mem.update({register: register_value})
        except:
            window.addst('No operation conducted.' + '\n')
            window.refresh()
            input = get_user_input(window, None, None, "")

    return stack, mem


def mem_recall(stack, mem, window):  # command: MR
    """Puts the value in the selected memory register on the stack.

Example:
    12 MR

puts the value of the #12 memory register on the stack.

Type:

    ML

to inspect (list) the memory registers."""
    if Decimal(stack[0]) == int(stack[0]) and stack[0] > 0:
        register = int(stack[0])
    else:
        window.addstr('='*45 + '\n')
        window.addstr('Register numbers are positive integers, only.' + '\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")

    # first, make sure the register exists in {mem}
    if register in mem.keys():
        stack.pop(0)
        stack.insert(0, mem[register])
    else:
        window.addstr('='*45 + '\n')
        window.addstr('Memory register' + '\n' + str(int(stack[0])) + '\n' + 'does not exist.' + '\n')
        window.addstr('Use\n\n\tML\n\nto list registers.' + '\n')
        window.addstr('='*45 + '\n')
        window.refresh()
        input = get_user_input(window, None, None, "")

    return stack, mem


def mem_list(stack, mem, window):  # command: ML
    """List all elements of memory register.

To create a memory register, use M+ or M-. Example:

     1 42 M+

This command creates register 1 and adds "42" to it."""
    # dictionaries are not sorted, so temporarily
    # sort {mem} by key (register number)
    sorted_mem = dict(sorted(mem.items()))

    if mem:
        window.addstr('\n' + '='*15 + ' MEMORY STACK ' + '='*16 + '\n')
        for k, v in sorted_mem.items():
            window.addstr('Register ' + str(int(k)) + ': ' + str(v) + '\n')
        window.addstr('='*45 + '\n\n')

    else:
        window.addstr('\n' + '='*55 + '\n')
        window.addstr('\nNo memory registers exist at this time. Sorry.\n\n')
        window.addstr('For help, type:\n\n')
        window.addstr('   h M+   or   h M-\n\n')
        window.addstr('='*55 + '\n\n')

    window.refresh()
    input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    return stack, mem


def mem_del(stack, mem, window):  # command: MD
    """Delete one, or a range, of memory registers. When
deleting a range of registers, the order of the
register numbers in x: and y: does not matter.
Deletion is inclusive of the numbers you enter.
Because, registers are identified with integers, the
numbers in x: (and y:) need to be integers.

NOTE 1: Make sure the stack is clear before entering
    register numbers since, pending confirmation,
    this operation uses whatever numbers appear in
    x: and y: as the range of registers to delete.

NOTE 2: Floats (e.g., 2.3) in x: or y: will be converted
to integers. The resulting register numbers may or may
not be what you intended.

Example (1):
    1 MD --> deletes #1 memory register

Example (2):
    10 3 MD --> deletes memory registers #3 to #10,
                inclusive

Example (3):
    4 MD --> deletes memory register 4; if a value,
    say 8, was left accidentally in y:, then a range
    of registers from 4 to 8 will be deleted.
    Confirmation before deletion prevents disaster in
    such cases.

Type:

    ML

to inspect (list) the memory registers."""

    # NOTE: Get the register numbers from stack[0] and stack[1]. Register numbers must be positive integers greater than zero. There is no register -0-.
    register1, register2 = int(abs(stack[0])), int(abs(stack[1]))

    # Make sure register2, if it isn't -0-, is >= register1
    if (register1 > register2) and (register2 != 0):
        register1, register2 = register2, register1

    # If user wants to delete only a single register. In this case, register2 is 0.
    if register2 == 0:
        prompt = '\nAre you sure you want to delete register ' + str(register1) + '? (Y/N) '
        confirm = get_user_input(window, None, None, prompt)
        if confirm.upper() == 'Y':
            try:
                mem.pop(Decimal(str(register1)))
            except KeyError:
                input = get_user_input(window, None, None, "\nMemory register " + str(register1) + " does not exist.\nPress <ENTER> to continue...")
            return stack, mem
        else:
            return stack, mem

    # If user wants to delete a range of registers.
    else:
        prompt = '\nAre you sure you want to delete all registers\n' + 'between register ' + str(register1) + ' and register ' + str(register2) + ', inclusive? (Y/N) '
        confirm = get_user_input(window, None, None, prompt)

        register_names = []
        if confirm.upper() == 'Y':

            # Remove registers between register1 and register2, inclusive.
            for i in range(register1, register2+1):

                # Convert the register number to a potential key in {mem}.
                r = Decimal(str(i))

                # NOTE: If a KeyError is raised, then one or more memory registers that the user wants to delete do not exist. Delete registers up to the KeyError, but abort because one cause of such an error is if the user wants to delete registers 1 to 100, when 1 to 10 was intended. We don't want 100 messages to display.

                try:

                    mem.pop(r)
                    # Keep track of which registers have been deleted so far... maybe only 1!
                    register_names.append(str(i))

                except KeyError:
                    if register_names:

                        # Make a single string out of the register numbers in "register_names".
                        register_names = ', '.join(register_names)
                        # Report out to the user which registers have been deleted and that deletion is now going to be aborted (due to a KeyError).

                        if len(register_names) > 1:
                            window.addstr("\nRegisters " + register_names + " were deleted.\n")
                            window.addstr("\nOne or more memory registers between " + str(register1) + " and " + str(register2) +
                                          " do not exist.\n\nUse <ML> to inspect a list of the memory registers.\n")

                        else:
                            window.addstr("\nRegister " + register_names + " was deleted.\n")
                            window.addstr("\nOne or more memory registers between " + str(register1) +
                                          " and " + str(register2) + " do not exist.\n\nUse <ML> to inspect a list of the memory registers.\n")
                            window.refresh()
                            input = get_user_input(window, None, None, "\nPress <ENTER> to continue...")

                    else:
                        window.addstr("\nNo registers were deleted. Use <ML> to inspect\na list of the memory registers.\n")
                        window.refresh()
                        input = get_user_input(window, None, None, "\nPress <ENTER> to continue...")

                    # NOTE: Putting "return" here exits after the first KeyError, preventing a very long loop if the user enters a huge number as register 2.
                    return stack, mem

            return stack, mem
        else:
            return stack, mem


# ==== HELP and TUTORIALS =======================

def help(stack, item, window):    # command: help
    """For help on help, type:
        help"""

    txt = """
=================== HELP ====================
Type:
    index: table of contents of calculator commands
   basics: the basics of RPN
 advanced: how to use THIS calculator
userhelp: how to create user-defined operations
  phrases: a list of user-friendly phrases

You can also type:

    h [command]

to get information about a specific command. Example:

    h sqrt
============================================="""

    show_help(window, txt)

    return stack


def help_fxn(stack, item, window):
    """Help for a single command.

Example:

    h sqrt --> Find the square root of x:.
    """

    if item in op1.keys():
        f = op1[item]
    elif item in op2.keys():
        f = op2[item]
    elif item in commands.keys():
        f = commands[item]
    elif item in constants.keys():
        f = constants[item]
    elif item in shortcuts.keys():
        f = shortcuts[item]
    else:
        input = get_user_input(window, None, None, '\nHelp not found.\nPress <ENTER> to continue...')
        return stack

    # Now that you have the function name, go back to func and get the docString
    docstring_text = f[0].__doc__.splitlines()

    window.addstr('\n' + '='*55 + '\n\n')
    max_terminal_rows, max_terminal_cols = get_terminal_dims(window)

    row_num, line_width = 10, 56
    for ndx, i in enumerate(docstring_text):
        row_num += 1
        if row_num == max_terminal_rows - 4:
            r, c = max_terminal_rows - 4, 29
            window.addstr('\n')
            input = get_user_input(window, None, None, "Press <ENTER> to continue...")
            window.move(9, 0)
            window.clrtobot()
            window.move(9, 0)
            window.refresh()
            row_num = 9

        window.addstr(i + '\n')
        window.refresh()

    window.addstr('\n' + '='*55 + '\n')
    window.addstr('\n')
    window.refresh()

    input = get_user_input(window, None, None, "Press <ENTER> to continue...")

    return stack


def basics(stack, item, window):
    """The basics of RPN.

Type:

    basics

to display an introduction to how RPN calculators
work."""
    txt = """============= HELP: RPN BASICS ==============
A RPN (reverse polish notation) calculator has no "equals" < = > key. Rather, numbers are placed on a "stack" and then one or more operations are invoked to act on the stack values. The results of most operations are placed back on the stack. The size of the stack is limited by computer memory but can easily hold millions of numbers (good luck with that!). However, the first four items, or registers, in the stack, have names: x: (keyboard), y: (accumulate), z: (temporary), and t: (top).

Here's an example of how RPN works:

Type:

    3 <ENTER>      4 <ENTER>

Result:

    t:          0.0000
    z:          0.0000
    y:          3.0000
    x:          4.0000

When 3 is entered, it goes to the x: register. Then, when 4 is entered, 3 is moved to the y: register and 4 is placed in the x: register. Now, you can do anything you want with those two numbers. Let's add them.

Type:

    + <ENTER>

The x: and y: registers are added, and the result (7) appears on the stack.

The speed of RPN is realized when entering complicated operations all on one line:

Type:

    3 4 dup + +

ada parses the whole operation at once. After "dup" (duplicate), the stack looks like this:

    t:          0.0000
    z:          3.0000
    y:          4.0000
    x:          4.0000

The first + adds y: (4) and x: (4) to yield 8.

    t:          0.0000
    z:          0.0000
    y:          3.0000
    x:          8.0000

The second + adds the new y: and the new x: to yield 11.

    t:          0.0000
    z:          0.0000
    y:          0.0000
    x:         11.0000

You can also group items using parentheses (nested groups are allowed!).

Example:

    (145 5+)(111 20+) *

The result of the first group is placed on the stack in x:. Then it is moved to y: when the second group is executed and placed in x:. Then the multiplication operator multiplies x: and y:. This type of operation is where the real power of RPN is realized.

Reverse polish notation makes it possible to never use parentheses, but they sure help us humans! Try the above calculation with and without parentheses and you'll see that the result is the same. On a non-RPN calculator, performing this calculation with and without grouping results in different values.
============================================="""

    show_help(window, txt)

    return stack


def advanced(stack, item, window):
    """Advanced help: how to use this calculator: ada.

Type:

    advanced

for information about advanced use of RPN and, in
particular, this command-line calculator."""

    txt = """=========== HELP: HOW TO USE ada ============

INTRO and PRECISION
ada is a command line calculator, designed for speed of both user interaction and calculations. Results of calculations are accurate to 28 decimal places due to use of python's "decimal" package. Most calculators use a "float" number type with an accuracy to 14 places. For example, using the "float" number type:

    0.1 / 0.3 =  0.3333333333333333703407674875

Whereas, using the "decimal" number type:

    0.1 / 0.3 = 0.3333333333333333333333333333


OPERATIONS and HELP
You can get a list of available calculator operations by typing:

    index

or more detailed information by typing:

    h [command]

where [command] is any command in the lists of commands, operations, and shortcuts. All of the common calculator operations are available.

Numbers entered in a sequence MUST be separated by spaces, for obvious reasons. A single shortcut can follow a number directly, but sequences of shortcuts or operations using words must use spaces. For examples of valid and invalid operations, put the following numbers on the stack:

    t:          0.0000
    z:          4.0000
    y:          7.0000
    x:          3.0000

We want to drop 3, swap 4 and 7, then get the square root of the x: register (4), to yield the result: 2.0. Valid and invalid operations:

    (1) 4 7 3 d s sqrt (valid)
    (2) 4 7 3d s sqrt  (valid)
    (3) 4 7 3ds sqrt   (invalid)
    (4) 4 7 3 dssqrt   (invalid)

Why "dssqrt" is invalid should be clear. The computer can't know what you meant. Was it "d s s qrt", with the last command being a mistake) or "d s sqrt"? The easiest rule (though it's not really a rule) is to put spaces between every item in the command line. Except for functions related to the memory registers (M+, MR, etc.), commands/operators use lower case only. Not having to use the <shift> key increases speed of entry.

THE TAPE
ada keeps track of operations you use, and these can be displayed by typing:

    tape

The tape provides a running list of operations entered during the current session. Type:

    h tape

for more information about the tape.


ADDITIONAL FEATURES
Besides the stack, ada provides three other features of interest. Type:

    h [related commands]

for more detailed information on each of the three.

1. Memory registers: These registers are nearly unlimited in number and are separate from the stack. They are identified by integers (register 1, register 2, etc.). You can add to or subtract from these registers, delete registers, and list contents of all registers you have created. Contents of registers that you recall (MR) are placed on the stack. Memory registers are saved between sessions. Incorporating memory register in user-defined operations can be particularly useful. [related commands: M+, M-, MR, MD, and ML]

2. User-defined operations: These provide a means for extending the available operations. You can store constants or whole operations, by name. User-defined operations are saved between sessions. [related commands: user, userop]

3. Conversion between RGB and hex colors, including alpha values. [related commands: alpha, rgb, and hex]

There's more! Explore the index and h [command] to see more of ada's capabilities.
============================================="""

    show_help(window, txt)

    return stack


def user_defined_help(stack, item, window):  # command: userhelp
    """Get help on how to define, edit, or delete user-defined
operations or constants.

    Type:

        user

    to create a user-defined operation.

    Type

        usercon

    to list currently available user-defined constants
    and operations."""

    txt = """Define, edit, or delete a user-defined operation or constant. A common use-case for user-defined operations would be to add a conversion that is not included in the base calculator. For example, the calculator can convert Fahrenheit temperatures to centigrade. What if you needed to convert Fahrenheit to degrees Kelvin? Simply create a user-defined operation that takes the x: register value and uses it in a formula:

    (°F − 32) × 5/9 + 273.15 = K

On an RPN calculator, the formula would be:

    (x: 32 -) 5 x 9 / 273.15 +
        where x: is the value in the x: register.

Name that operation however you want and there you have it!

Once defined, constants/operations are saved to file and they are retrieved automatically when the calculator starts. Names must be lower case and cannot contain spaces. You cannot redefine system names (e.g., "swap" or "clear"). You can define two types of named operations:

(1) Numerical constants. These are numbers.

    Example:
        ultimate:  42.0  [life's meaning]

(2) Operations. These are strings.

    Example (1):
        (150 140 -) 2 / 140 +

    Example (2):
        (y: x: - ) 2 / 140 +

The latter example show use of register names in an operation. Here is how to construct these types of operation. Let's create this operation:

    (x: y: +) y: *

What this expression does: User puts three numbers on the stack. The user-defined operation adds the last two numbers, then multiplies the result by the first number that was entered.

NOTE: Keep in mind that during evaluation of the operation, the stack contents change as operations are executed. We'll see this happen in this example...

-- Let's put the following three values on the stack.

    z:          7.0000
    y:          3.0000
    x:          1.0000

-- When the operation [ (x: y: +) y: * ] is run, the + operator adds x: and y:. y: is removed and x: is replaced with the result: 4. z: drops down to the y: register:

    z:          0.0000
    y:          7.0000
    x:          4.0000

-- Then the current x: and y: are multiplied and the result, 28, is put in the x: register:

    z:          0.0000
    y:          0.0000
    x:         28.0000

NOTES:
(1) The non-obvious point is that, in an operation, the registers (e.g., "x:") are not variable names, but refer to the stack at THAT point in the operation's execution.

(2) Register names can save a lot of time when repeating simple calculations, such as getting the mid-point between two values. Create and save the following operation, say as "mid".

    y: x: s dup rd - 2 / s d +

Put any two values on the stack, and run the operation by typing:

    mid

An easy way to get an operation: use the command line to do what you need, then copy the steps from the tape. Format into one line, if needed, and then paste (CTRL-V, not CTRL-v) the operation into the VALUE field when you create the user-defined operation using:

    user

(3) User-define constant/operation names cannot be used as part of a sequence on the command line.

For example:

    100 50 mid  -- invalid

    100 50      -- put values on stack first
    mid         -- valid

(4) Memory registers can act as variables, and may be better suited for some complicated operations. See help for M+, M-, MR, MD, and ML (e.g., h M+ or h MR)

Type:

    userop

to list the current user-defined operations."""

    show_help(window, txt)

    return stack


def show_help(window, txt):
    max_terminal_rows, max_terminal_cols = get_terminal_dims(window)
    help_text = '\n'.join([fold(txt, max_terminal_cols-2) for txt in txt.splitlines()])
    help_text = help_text.split('\n')

    row_num = 9
    window.move(9, 0)
    for i in help_text:
        if row_num == max_terminal_rows - 5:
            input = get_user_input(window, None, None, "\nPress <ENTER> to continue...")
            window.move(9, 0)
            window.clrtobot()
            window.move(9, 0)
            row_num = 9
            window.refresh()
        row_num += 1
        window.move(row_num, 0)
        window.addstr(i + '\n')

    window.addstr('\n')
    window.refresh()

    input = get_user_input(window, None, None, "\nPress <ENTER> to continue...")

    return None


def fold(txt, max_terminal_cols=55):
    """
    Textwraps 'txt'; used by help_fxn(), help(), basics(), and advanced().
    """
    return textwrap.fill(txt, width=max_terminal_cols)


# ==== UTILITY FUNCTIONS =============================

def get_current_yx(window):
    """
    Get the current cursor position.

    Args:
        window ([curses.window]): current window

    Returns:
        current_location[0] -- [int], cursor location in y direction (rows)
        current_location[1] -- [int], cursor location in x direction (columns)
    """
    current_location = window.getyx()
    return current_location[0], current_location[1]


def get_terminal_dims(window):
    """
    Get the dimensions of the current window.

    Args:
        window ([curses.window]): current window

    Returns:
        max_terminal[0] -- int, y dimension of terminal (rows)
        max_terminal[1] -- int, x dimension of terminal (columns)
    """
    max_terminal = window.getmaxyx()
    return max_terminal[0], max_terminal[1]


def get_user_input(window, current_row, current_col, prompt_string):
    """
    As a replacement for input(), this function that gets users' input in the current window.

    If current_row and/or current_col are "None", then this function will determine the current location of the cursor, which will be at the end of "prompt_string".

    Args:
        window ([curses.window]): [the current terminal window]
        current_row ([int]): [the current location (row) of the cursor]
        current_col ([int]): [the current location (column) of the cursor]
        prompt_string ([str]): [what the prompt should read]

    Returns:
        [str]: [the user's input, converted from bytes to str]
    """

    window.addstr(prompt_string)

    if current_row == None or current_col == None:
        current_row, current_col = get_current_yx(window)

    curses.echo()
    input = window.getstr(current_row, current_col).decode(encoding='utf8')

    curses.noecho()
    return input


def get_revision_number():
    """
    Manually run this function to get a revision number by uncommenting the first line of code under "if __name__ == '__main__':"
    """
    from datetime import datetime

    start_date = datetime(2021, 9, 10)
    tday = datetime.today()
    revision_delta = datetime.today() - start_date

    return revision_delta


def check_terminal_specs(window):
    """
    Determine if terminal is large enough to accomodate the calculator's functions. Column width is set at a minimum of 58 since the first line of the default menu is 55 characters wide.

    Args:
        window (curses.window): current terminal window
    """

    terminal_rows, terminal_cols = get_terminal_dims(window)

    rows_flag = True if terminal_rows < 29 else False
    cols_flag = True if terminal_cols < 58 else False
    terminal_too_small = True if rows_flag or cols_flag else False

    return terminal_too_small


def about(stack, item, window):   # command: about
    """Information about the author and program."""
    rev_number = get_revision_number()
    version_num = '4.0 rev ' + str(rev_number.days)

    window.addstr('\n' + '='*45 + '\n')

    txt1 = 'ada - an RPN calculator\n\n' + \
        '  version: ' + version_num + '\n' + \
        '   author: Richard E. Rawson\n\n'

    txt2 = 'ada is named after Ada Lovelace (1815–1852), whose achievements included developing an algorithm showing how to calculate a sequence of numbers, forming the basis for the design of the modern computer. It was the first algorithm created expressly for a machine to perform.'

    window.addstr('\n'.join([fold(txt1) for txt1 in txt1.splitlines()]) + '\n')
    window.addstr('\n'.join([fold(txt2) for txt2 in txt2.splitlines()]) + '\n')

    window.addstr('='*45 + '\n\n')
    window.refresh()

    input = get_user_input(window, None, None, 'Press <ENTER> to continue...')
    return stack


def version(stack, item, window):  # command: version
    """Program, python, and module version info."""
    rev_number = get_revision_number()
    revision_date = 'Last update: 2021-11-20'
    version_num = 'ada 4.01 rev ' + str(rev_number.days)
    window.addstr('\n' + '='*45 + '\n')
    window.addstr(version_num[0:18] + '\n')
    window.addstr(revision_date + '\n\n')
    txt = '    python: 3.8.0\n' + \
        '    curses: 2.2\n' + \
        '      json: 2.0.9\n' + \
        ' pyperclip: 1.8.2\n\n'
    window.addstr(txt)
    window.addstr('='*45 + '\n\n')
    window.refresh()
    input = get_user_input(window, None, None, 'Press <ENTER> to continue...')

    return stack


def main(window):
    """
    Main function used to invoke curses.wrapper().

    Args:
        window (curses.window): current window object

    Returns: None
    """

    RPN(stack, user_dict, lastx_list, mem, settings, tape, window)

    return None


def list_defs():
    """
    Generate list of functions and, optionally, docstrings for each function.
    https://medium.com/python-pandemonium/python-introspection-with-the-inspect-module-2c85d5aa5a48

    Last update:
        RPN, parse_entry, initial_processing, process_item, find_error,
        print_register, get_file_data, manual, print_commands, print_phrases,
        print_math_ops, print_shortcuts, print_constants, print_dict,
        print_info_utility, calculator_settings, log, ceil, floor,
        factorial, negate, sin, cos, tan, asin, acos, atan, pi_value,
        deg, rad, absolute, random_number, add, sub, mul, truediv,
        mod, power, math_op1, math_op2, convert_bin_to_dec, convert_dec_to_bin,
        convert_dec_to_hex, convert_hex_to_dec, user_defined, clear,
        drop, dup, get_lastx, list_stack, print_tape, roll_up, roll_down,
        round_y, split_number, sqrt, stats, swap, trim_stack, hex_to_rgb,
        rgb_to_hex, get_hex_alpha, list_alpha, ci, ic, lengths,
        ftoc, ctof, go, og, kp, pk, km, mk, cm, mc, mem_add, mem_sub,
        mem_recall, mem_list, mem_del, help, help_fxn, basics, advanced,
        user_defined_help, show_help, fold, get_current_yx, get_terminal_dims,
        get_user_input, get_revision_number, check_terminal_specs,
        about, version, main
    """
    import ast

    with open('ada.py', 'r') as fd:
        file_contents = fd.read()
    module = ast.parse(file_contents)
    function_definitions = [
        node for node in module.body if isinstance(node, ast.FunctionDef)]

    function_list = []
    for f in function_definitions:
        function_list.append(f.name)
        # print(f.name)
        # print(ast.get_docstring(f))
        # print('\n')

    # function_list.sort()
    print(function_list)

    return None


# ==== ESTABLISH GLOBAL ENVIRONMENT (VARIABLES, etc.) =================================

if __name__ == '__main__':
    """
    Read or create config.json, that contains settings chosen by the user.

    Then, initialize a host of global variables, including the x:, y:, z:, and t: registers. Creating universally accessible global variables saves having to pass a large number of variables, that never change, between functions. Global variables include:

             menu -- (tuple), menu items
              op1 -- {dict}, operations that modify or use x: only
              op2 -- {dict}, operations that require both x: and y:
         commands -- {dict}, analogous to verbal commands such as "roll down" or "swap"
        constants -- {dict}, physical constants
        shortcuts -- {dict}, shortcut keys for commands
            alpha -- {dict}, alpha codes for transparency values
          phrases -- {dict}, short phrases that make some conversion commands easier
          letters -- string, all upper- and lower-case letters, underscore, and colon
    lower_letters -- string, lower-case letters, underscore, underscore, and colon

    Other variables set here, but that are modified by the program, include:

            stack -- [list], holds the stack; unlimited length
    entered_value -- float, the command line entry
    # !lastx_list -- [list], stores the last x: value
              mem -- {dict}, dictionary of memory registers; saved between sessions
             tape -- [list], the "tape"

    """

    stack, entered_value = [Decimal('0.0')], 0.0
    lastx_list, tape = [Decimal('0.0')], []
    letters = ascii_letters + '_' + ':'
    lower_letters = ascii_lowercase + '_' + ':'

    # Initialize setup by saving default settings to config.json.
    # If the file already exists, then put contents in {settings}.
    try:
        with open("config.json", 'r') as file:
            settings = json.load(file)
    except FileNotFoundError:
        settings = {
            'dec_point': '4',
            'separator': ','
        }
        # If config.json does not exist, create it.
        with open('config.json', 'w+') as file:
            file.write(json.dumps(settings, ensure_ascii=False))

    # Menu gets printed on screen 4 items to a line.
    menu = (
        '<d>rop       ', '<s>wap       ', '<r>oll <u>p      ', '<r>oll<d>own',
        '<n>eg        ', '<c>lear      ', '<userop>erations ', '<user>',
        '<set>tings   ', '<index>      ', '<help>           ', '<q>uit       '
    )

    # Operations that use or modify x: only (stack[0]).
    op1 = {
        "": ('', ''),
        "====": ('', '==== GENERAL ==========================='),
        "abs": (absolute, "absolute value of x:"),
        "ceil": (ceil, "6.3->7"),
        "!": (factorial, "x: factorial"),
        "floor": (floor, "6.9->6"),
        "log": (log, "log10(x:)"),
        "n": (negate, "negative of x:"),
        # "negate": (negate, "Get the negative of x."),
        "pi": (pi_value, "pi"),
        "rand": (random_number, 'random int between x: and y:'),
        "round": (round_y, 'round y: by x:'),
        "sqrt": (sqrt, "sqrt(x:)"),
        " ": ('', ''),
        " ====": ('', '==== TRIGONOMETRY ======================'),
        "cos": (cos, "cos(x:) -- x: must be radians"),
        "sin": (sin, "sin(x:) -- x: must be radians"),
        "tan": (tan, "tan(x:) -- x: must be radians"),
        "acos": (acos, "acos(x:) -- x: must be radians"),
        "asin": (asin, "asin(x:) -- x: must be radians"),
        "atan": (atan, "atan(x:) -- x: must be radians"),
        "deg": (deg, "convert angle x: in radians to degrees"),
        "rad": (rad, "convert angle x: in degrees to radians"),
        "  ": ('', ''),
        "  ====": ('', '==== CONVERSIONS ======================='),
        'decbin': (convert_dec_to_bin, 'Convert x: from decimal to binary.'),
        "bindec": (convert_bin_to_dec, 'Convert "0b..." from binary to decimal.'),
        "dechex": (convert_dec_to_hex, 'Convert x: from decimal to hex.'),
        "hexdec": (convert_hex_to_dec, 'Convert "0x..." from hex to decimal.'),
        'ic': (ic, 'Convert inches to centimeters.'),
        'ci': (ci, 'Convert centimeters to inches.'),
        'cf': (ctof, 'Convert centigrade to Fahrenheit.'),
        'fc': (ftoc, 'Convert Fahrenheit to centigrade.'),
        'go': (go, 'Convert weight from grams to ounces.'),
        'og': (og, 'Convert weight from ounces to grams.'),
        'i': (lengths, 'Convert decimal measure to fraction.'),
        'kp': (kp, 'Convert kilograms to pounds.'),
        'pk': (pk, 'Convert pounds to kilograms.'),
        'km': (km, 'Convert kilometers to miles.'),
        'mk': (mk, 'Convert miles to kilometers.'),
        'cm': (cm, 'Convert cmH2O to mmHg.'),
        'mc': (mc, 'Convert mmHg to cmH2O.')
    }

    # Operations that __require__ both x: and y: (stack[0] and stack[1]).
    op2 = {
        "    ": ('', ''),
        "====": ('', '==== STANDARD OPERATORS ================'),
        "+": (add, "y: + x:"),
        "-": (sub, "y: - x:"),
        "*": (mul, "y: * x:"),
        "x": (mul, "y: * x:"),
        "/": (truediv, "y: / x:"),
        "%": (mod, "modulo; remainder after division"),
        "^": (power, "y: to the power in x:"),
    }

    # General commands that provide functions beyond math operators.
    commands = {
        "      ====": ('', '==== GENERAL ==========================='),
        "about": (about, "Info about the author and product."),
        "import": (get_file_data, "Import data from a text file."),
        'set': (calculator_settings, 'Access and edit settings.'),
        'version': (version, 'Program, python, and module version info.'),
        "     ": ('', ''),
        " ====": ('', '==== COLOR ============================='),
        'alpha': (get_hex_alpha, 'Hex equivalent of RGB alpha value.'),
        'hex': (rgb_to_hex, 'Convert rgb color (z:, y:, x:) to hex color.'),
        "list_alpha": (list_alpha, "List all alpha values."),
        'rgb': (hex_to_rgb, 'Convert hex color to rgb.'),
        "      ": ('', ''),
        "  ====": ('', '==== HELP =============================='),
        'help': (help, 'How to get help.'),
        "index": (manual, "Menu to access parts of the manual."),
        "basics": (basics, "The basics of RPN."),
        "advanced": (advanced, 'Advanced help: how to use ada.'),
        "com": (print_commands, "List all commands and math operations."),
        "math": (print_math_ops, "List math operations."),
        "con": (print_constants, 'List constants.'),
        "short": (print_shortcuts, 'Available shortcuts.'),
        "userhelp": (user_defined_help, 'How to create user-defined operations.'),
        "phrases": (print_phrases, 'List available phrases.'),
        "       ": ('', ''),
        "   ====": ('', '==== MEMORY REGISTERS =================='),
        "M+": (mem_add, 'Add x: to y: memory register.'),
        "M-": (mem_sub, 'Subtract x: from y: memory register.'),
        "MR": (mem_recall, 'Put x: register value on stack.'),
        "MD": (mem_del, 'Delete one or all memory registers.'),
        "ML": (mem_list, 'List elements of memory register.'),
        "        ": ('', ''),
        "    ====": ('', '==== STACK MANIPULATION ================'),
        "clear": (clear, "Clear all elements from the stack."),
        "drop": (drop, "Drop the last element off the stack."),
        "dup": (dup, "Duplicate the last stack element."),
        # ! "lastx": (get_lastx, "Put the last x: value on the stack."),
        "list": (list_stack, "Show the entire stack."),
        "rolldown": (roll_down, "Roll stack down."),
        "rollup": (roll_up, "Roll stack up."),
        "split": (split_number, "Splits x: into integer and decimal parts."),
        'stats': (stats, 'Summary stats (non-destructive).'),
        "swap": (swap, "Swap x: and y: values on the stack."),
        'tape': (print_tape, "Display tape from current session."),
        "trim": (trim_stack, 'Remove stack, except the x:, y:, z:, and t:.'),
        "         ": ('', ''),
        "     ====": ('', '==== USER-DEFINED ======================'),
        "userop": (print_dict, "List user-defined operations."),
        "user": (user_defined, 'Add/edit user-defined operations.'),
    }

    # Values obtained from: http://www.onlineconversion.com
    # constant names MUST be lowercase.
    # NOTE: The Decimal type has a default precision of 28 places, while the float has 18 places.
    constants = {
        "e": (Decimal('2.7182818284590452353602874714'), 'e (Euler\'s number)'),
        "avogadro": (Decimal('6.0221409e+23'), "Avogadro's number"),
        "golden_ratio": (Decimal('1.61803398874989484820'), 'golden ratio'),
        "gram": (Decimal('0.03527396195'), "ounces in a gram"),
        "inches_hg": (Decimal('25.399999705'), "inches of Hg in a mmHg"),
        "light":  (Decimal('299792458'), "speed of light, m/s"),
        "mmhg": (Decimal('0.53524017145'), "inches of water in a mmHg"),
        "parsec": (Decimal('19173510995000'), 'miles in a parsec'),
    }

    shortcuts = {
        'c': (clear, 'Clear all elements from the stack'),
        'd': (drop, 'Drop the last element off the stack'),
        'h': (help, 'Help for a single command'),
        'n': (negate, 'Negative of x:'),
        'q': ('', 'Quit'),
        'r': (round_y, 'round y by x:'),
        'rd': (roll_down, 'Roll the stack down'),
        'ru': (roll_up, 'Roll the stack up'),
        's': (swap, 'Swap x: and y: values on the stack'),
    }

    # Keys are "percent transparency" and values are "alpha code" for hex colors; 0% is transparent; 100% is no transparency.
    alpha = {
        '100': 'FF',
        '95': 'F2',
        '90': 'E6',
        '85': 'D9',
        '80': 'CC',
        '75': 'BF',
        '70': 'B3',
        '65': 'A6',
        '60': '99',
        '55': '8C',
        '50': '80',
        '45': '73',
        '40': '66',
        '35': '59',
        '30': '4D',
        '25': '40',
        '20': '33',
        '15': '26',
        '10': '1A',
        '5': '0D',
        '0': '00'
    }

    phrases = {
        'decimal to binary': ('decbin', 'Convert decimal to binary.'),
        # 'binary to decimal': ('bindec', 'Convert "0b..."from binary to decimal.'),
        'decimal to hex': ('dechex', 'Convert decimal to hex.'),
        # 'hex to decimal': ('hexdec', 'Convert "0x..." from hex to decimal.'),
        'inches to centimeters': ('ic', 'Convert inches to centimeters.'),
        'centimeters to inches': ('ci', 'Convert centimeters to inches.'),
        'centigrade to fahrenheit': ('cf', 'Convert centigrade to Fahrenheit.'),
        'fahrenheit to centigrade': ('fc', 'Convert Fahrenheit to centigrade.'),
        'grams to ounces': ('go', 'Convert from grams to ounces.'),
        'ounces to grams': ('og', 'Convert from ounces to grams.'),
        'decimal to fraction': ('i', 'Convert decimal to fraction.'),
        'kilograms to pounds': ('kp', 'Convert kilograms to pounds.'),
        'pounds to kilograms': ('pk', 'Convert pounds to kilograms.'),
        'kilometers to miles': ('km', 'Convert kilometers to miles.'),
        'miles to kilometers': ('mk', 'Convert miles to kilometers.'),
        'cm water to mmhg': ('cm', 'Convert cm water to mmHg.'),
        'mmhg to cm water': ('mc', 'Convert mmHg to cm water.'),
        # The rest of this dictionary holds keys that might be type by the user because, well, they make sense.
        'userops': ('userop', ''),
        'user operations': ('userop', ''),
        'useroperations': ('userop', ''),
    }

    """
    When calculator starts, read constants.json if it exists. This way, the user has access to user-defined operations without having to do anything special
    """
    try:
        with open("constants.json", 'r') as file:
            user_dict = json.load(file)
    except FileNotFoundError:
        user_dict = {}
    try:
        with open("memory_registers.json", 'r') as file:
            memory = json.load(file)
            mem = {Decimal(k): Decimal(v) for k, v in memory.items()}
    except:
        mem = {}

    # Confirm that the terminal size is appropriate. If so, run main().
    terminal_too_small = curses.wrapper(check_terminal_specs)
    curses.endwin
    if terminal_too_small:
        print("|")
        print("| Terminal must be at least 58 wide. It must be 29")
        print("| high to use multi-line functions, such as 'HELP'")
        print("| or 'INDEX'.")
        print("|")
        print("|")
        print("| <=== 58 wide =========================================>")
        for i in range(20):
            try:
                print("|")
            except:
                break

        print("| Set terminal dimensions using these guide lines.\n")
        input = input("Press <ENTER> to exit...")
    else:
        curses.wrapper(main)

    # When the program exits, print the program name,
    # version number, and a short description.
    txt1 = '\nada v4.0 - an RPN calculator' + '\n'
    print(txt1)
