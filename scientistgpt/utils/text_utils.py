import textwrap
import re
import colorama


def dedent_triple_quote_str(s: str):
    """
    Format a triple-quote string to remove extra indentation and leading newline.
    """
    return textwrap.dedent(s).lstrip()


def wrap_string(input_string, width=40, indent=0):
    """
    Add linebreaks to wrap a long string.
    """
    # split input string into lines
    lines = input_string.splitlines()
    wrapped_lines = []

    # wrap each line individually
    for line in lines:
        wrapped_line = textwrap.fill(line, width=width)
        wrapped_lines.append(wrapped_line)

    # join wrapped lines back together with preserved line breaks
    wrapped_string = "\n".join(wrapped_lines)

    # add indent to each line if specified
    if indent > 0:
        wrapped_string = textwrap.indent(wrapped_string, ' ' * indent)

    return wrapped_string


def colored_text(text: str, color: str, is_color: bool = True) -> str:
    return color + text + colorama.Style.RESET_ALL if is_color else text


def red_text(text: str, is_color: bool = True) -> str:
    return colored_text(text, colorama.Fore.RED, is_color)


def print_red(text: str, **kwargs):
    print(colored_text(text, colorama.Fore.RED), **kwargs)


def print_magenta(text: str, **kwargs):
    print(colored_text(text, colorama.Fore.MAGENTA), **kwargs)


def format_text_with_code_blocks(text: str, text_color: str, code_color: str, width: int) -> str:
    def get_color(is_cd: bool):
        return code_color if is_cd else text_color

    text = wrap_string(text, width=width)
    is_code = False
    s = get_color(is_code)
    for line in text.splitlines():
        if '```' in line:
            is_code = not is_code
            s += get_color(is_code)
        else:
            s += line + '\n'
    if text_color or code_color:
        s += colorama.Style.RESET_ALL
    return s


def word_count(text):
    """
    Count the number of words in provided test.
    """
    return len(re.findall(r'\w+', text))