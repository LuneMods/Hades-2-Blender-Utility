import os
import subprocess

def gr2_to_dae(input_file):
    if not os.path.isabs(input_file):
        print(f"Error: The input file path '{input_file}' must be an absolute path.")
        return None

    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        return None
    if not input_file.lower().endswith(".gr2"):
        print(f"Error: Input file '{input_file}' is not a .gr2 file.")
        return None

    output_file = os.path.splitext(input_file)[0] + ".dae"

    addon_dir = os.path.dirname(os.path.abspath(__file__))
    divine_exe_path = os.path.join(addon_dir, "External", "lslib", "divine.exe")

    if not os.path.isfile(divine_exe_path):
        print(f"Error: Divine.exe not found at '{divine_exe_path}'.")
        return None

    command = [
        divine_exe_path,
        "-a", "convert-model",
        "-g", "bg3",
        "-s", input_file,
        "-d", output_file
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Divine.exe executed successfully!")
        print("STDOUT:")
        print(result.stdout)
        if os.path.isfile(output_file):
            print(f"DAE file created: {output_file}")
            return output_file
        else:
            print("DAE file was not created.")
            return None
    except subprocess.CalledProcessError as e:
        print("An error occurred while running Divine.exe.")
        print("STDOUT:")
        print(e.stdout)
        print("STDERR:")
        print(e.stderr)
        return None


def dae_to_gr2(input_file, export_path):
    if not os.path.isabs(input_file):
        print(f"Error: The input file path '{input_file}' must be an absolute path.")
        return None

    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        return None
    
    if not input_file.lower().endswith(".dae"):
        print(f"Error: Input file '{input_file}' is not a .dae file.")
        return None

    output_file = os.path.splitext(export_path)[0]

    addon_dir = os.path.dirname(os.path.abspath(__file__))
    divine_exe_path = os.path.join(addon_dir, "External", "lslib", "divine.exe")

    if not os.path.isfile(divine_exe_path):
        print(f"Error: Divine.exe not found at '{divine_exe_path}'.")
        return None

    command = [
        divine_exe_path,
        "-a", "convert-model",
        "-g", "bg3",
        "-s", input_file,
        "-d", output_file
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Divine.exe executed successfully!")
        print(result.stdout)
        if os.path.isfile(output_file):
            print(f"GR2 file created: {output_file}")
            return output_file
        else:
            print("DAE file was not created.")
            return None
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        return None