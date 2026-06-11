use std::fs::File;
use std::io;
use std::path::Path;

use sha2::{Digest, Sha256};

use crate::error::{RlabError, RlabResult};

pub fn sha256_file(path: &Path) -> RlabResult<String> {
    let mut file = open_file(path)?;
    let digest = sha256_reader(&mut file).map_err(|error| RlabError::io(path, error))?;

    Ok(hex::encode(digest))
}

fn open_file(path: &Path) -> RlabResult<File> {
    File::open(path).map_err(|error| RlabError::io(path, error))
}

fn sha256_reader(reader: &mut impl io::Read) -> io::Result<[u8; SHA256_DIGEST_BYTES]> {
    let mut hasher = Sha256::new();
    io::copy(reader, &mut hasher)?;

    Ok(hasher.finalize().into())
}

const SHA256_DIGEST_BYTES: usize = 32;
