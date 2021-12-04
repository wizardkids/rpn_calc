# **_ada_ - a command-line RPN calculator**

## **Why a command-line calculator?**
...because keyboard entry is so much faster than pointing and clicking or tapping buttons on a touch screen.

## **Why RPN?**
...because hitting an equals key is so 1995 and using RPN is demonstrably faster than a conventional calculator.

**_ada's exclusive goal_** is to provide an app that loads fast, executes fast, and is not bloated with capabilities that you will never use because there's Excel, Jupyter Notebooks, and SAS/STAT. For example, try this with any other kind of calculator:

   `4 16 s 2 ^ 4 / /`

Typing a single expression using only a keyboard, **_ada_** executes the line to result in x: 4. While parentheses (to group parts of an expression) are allowed, RPN makes parentheses unnecessary.

## **Features:**
- standard RPN number entry and execution with an unlimited stack size
- easy access to lists of available commands, operators,  constants, and user-defined operations
- extensive help, including specific help for every command and operator
- ability to use parentheses to group expressions in a single line
- read single-column data from an external file
- save your own constants or operations, which allows the user to extend the capability of the base calculator as needed
- unlimited memory registers
- a "tape" records all expressions entered during the current session
- descriptive statistics for numbers on the stack

...and there's more!

## **Installation:**
Installation could not be easier. **_ada_** requires one file: `ada.py`. If you have python 3.7+ installed, download `ada.py` and, assuming python.exe is in your PATH, run:

    python ada.py

In addition to the standard python package, the following packages are required:

    curses
    pyperclip
