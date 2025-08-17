from argparse import ArgumentParser
from pathlib import Path
import numpy as np

# Complete NRRD file format specification at:
# http://teem.sourceforge.net/nrrd/format.html
NHDR_TEMPLATE = """NRRD0004
content: {title}
# {comment}{extrafields}
# 
type: uchar
dimension: 4
space: left-posterior-superior
sizes: {Nz} {Ny} {Nx} {Nt}
space directions: (1,0,0) (0,1,0) (0,0,1) none
kinds: space space space list
endian: big
encoding: raw
space origin: (0.0, 0.0, 0.0)
byte skip: {header_size}
data file: {filename}
"""

def format_nhdr_header(npyfile, title="", extrafields=None, comment=None):
    if npyfile.suffix != ".npy":
        raise ValueError(f"File {npyfile} is not a .npy file")
    
    with npyfile.open("rb") as fhandle:
        major, minor = np.lib.format.read_magic(fhandle)
        assert major == 1  # Check npy format version
        assert minor == 0  # Check npy format version
        shape, fortran, dtype = np.lib.format.read_array_header_1_0(fhandle)
        assert dtype == np.uint8
        assert (len(shape) == 4) or (len(shape) == 3)
        header_size = fhandle.tell()

    if len(shape) == 3:
        shape = (1, *shape)

    if isinstance(extrafields, dict):
        extrafields = "\n" + "\n".join(f"{key}:= {value}" for key, value in extrafields.items())

    if comment is None:
        comment = ""
    elif isinstance(comment, list):
        comment = "\n".join(comment)

    return NHDR_TEMPLATE.format(
        Nz=shape[3],
        Ny=shape[2],
        Nx=shape[1],
        Nt=shape[0],
        header_size=header_size,
        filename=str(npyfile.name),
        comment="\n# ".join(comment.split("\n")),
        title=title,
        extrafields=extrafields,
    )

def generate_nhdr_header(npyfile, title="", comment=None, extrafields=None):
    header = format_nhdr_header(npyfile, title=title, comment=comment, extrafields=extrafields)
    outfile = npyfile.with_suffix(".seq.nhdr")
    outfile.write_text(header)
    return outfile

def main():
    parser = ArgumentParser()
    parser.add_argument("files", action="extend", type=Path, nargs='+')
    args = parser.parse_args()

    for file in args.files:
        try:
            outfile = generate_nhdr_header(file)
            print(f"Created {outfile}")
        except ValueError as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
