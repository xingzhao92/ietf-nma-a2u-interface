# Publish the v3.3 demo to GitHub

This directory is an overlay for:

`https://github.com/xingzhao92/ietf-nma-a2u-interface`

It contains:

- an updated root `README.md`;
- the v3.3 demo in `hackathon-demo/`;
- README screenshots in `docs/images/`.

## Recommended commands

```bash
git clone https://github.com/xingzhao92/ietf-nma-a2u-interface.git
cd ietf-nma-a2u-interface

# Copy the contents of this overlay into the cloned repository.
# Review README.md first if the repository has information that must be retained.
cp -a /path/to/ietf-nma-a2u-interface-github-ready/. .

git add README.md hackathon-demo docs/images
git status
git commit -m "Add NMA A2U Hackathon demo v3.3"
git push origin main
```

On Windows, copy the three overlay items (`README.md`, `hackathon-demo`, and
`docs`) into the cloned repository, then run the `git add`, `git commit`, and
`git push` commands.
