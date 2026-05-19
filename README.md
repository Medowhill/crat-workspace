# Setup

```bash
pip3 install libclang toml

git submodule init
git submodule update
python3 aws-translate/scripts/package/package.py -o `pwd`/bundles --root Test-Corpus -s Public-Tests
python3 aws-translate/scripts/package/package.py -o `pwd`/bundles --root PUBLIC-Test-Corpus -s Hidden-Tests

git clone https://github.com/Yale-PROCTOR/crat
pushd crat/deps_crate && cargo build && popd

./scripts/translate_all.py
./scripts/transform_all.py transformed bin --run-dependencies
./scripts/test_all.py transformed
```
