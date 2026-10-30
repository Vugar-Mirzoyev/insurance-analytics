"""Download the raw files into data/raw/.

Run from the project root:  python -m src.download

- CBAR Tables 6.1 and 6.2 (January-September 2026 release). CBAR publishes a new
  file every month on https://www.cbar.az/page-189/insurance; to update, put the
  new link here (or save the file as data/raw/cbar/cbar_6_1_<yyyy_mm>.xlsx).
- Lledó & Pavía motor portfolio, Mendeley Data, doi:10.17632/5cxyb5fp4f.2,
  CC BY 4.0. Checked against the SHA-256 published by Mendeley.
"""

import hashlib
import os
import urllib.request

MENDELEY = "https://data.mendeley.com/public-files/datasets/5cxyb5fp4f/files"
FILES = [
    ("data/raw/cbar/cbar_6_1_by_insurer_2026_09.xlsx",
     "https://uploads.cbar.az/assets/78a74c5d22fca5c002cd80b05.xlsx", None),
    ("data/raw/cbar/cbar_6_2_by_class_2026_09.xlsx",
     "https://uploads.cbar.az/assets/1ab5f20a98bf3ba73969dcac7.xlsx", None),
    ("data/raw/portfolio/Motor vehicle insurance data.csv",
     f"{MENDELEY}/e83f1f20-b93e-4971-97a4-5c9a2b7baeef/file_downloaded",
     "00061a64e355a7f9bbd06f1bcd3f0846b1f849955119a812acf2bc7781ee293a"),
    ("data/raw/portfolio/sample type claim.csv",
     f"{MENDELEY}/f06af09a-39fa-41e2-9ac1-31a70535531e/file_downloaded",
     "d35d967d66563ea291fd6d450cbfdf52f5118c5e7b3625b7b3a9bfa5a9361c3d"),
    ("data/raw/portfolio/Descriptive of the variables.xlsx",
     f"{MENDELEY}/965e3003-666a-4965-a7a2-ec5130ad1ad2/file_downloaded",
     "8b451e1898ca42e7092d4011c8e7071235fdc6e859a4e24070960580df433cc2"),
]


def download(path, url, sha256=None):
    """Fetch url into path unless it is already there; check the hash if one is given."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(url, path)
        print(f"Downloaded {path}")
    if sha256:
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        if digest != sha256:
            raise ValueError(f"{path}: SHA-256 {digest} does not match {sha256}")


if __name__ == "__main__":
    for path, url, sha256 in FILES:
        download(path, url, sha256)
    print("All files present.")
