import os
import sys

from maple import process_command


# ============================================================
# EXROOT WINDOWS APP
# ============================================================

def clear():

    os.system("cls")


def banner():

    print("""
============================================================
                         EXROOT
============================================================
 AI-native Windows terminal
 Maple / Groq / GPT-OSS-120B
============================================================

Type your CVE command.

Example:

    cve mkdir proj

Type "exit" to close EXROOT.
""")


def main():

    clear()
    banner()

    while True:

        try:

            current_directory = os.getcwd()

            print()
            command = input(
                f"EXROOT [{current_directory}] > "
            ).strip()

        except KeyboardInterrupt:

            print("\n")
            break

        except EOFError:

            break

        if not command:
            continue

        if command.lower() in [
            "exit",
            "quit"
        ]:
            break

        print()

        result = process_command(command)

        print(result)


if __name__ == "__main__":
    main()
