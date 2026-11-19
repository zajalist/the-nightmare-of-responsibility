# Publishing FoA on ModelScope (+20 h Notebook GPU)

## What the hackathon page says

The hackathon page (https://www.aholo.ai/hackathon, English and Chinese versions, read Nov 5) says: "We encourage participants to publish their projects on ModelScope and submit a valid project link on the official hackathon website. Once the submission has been verified and meets the requirements, participants can receive an additional 20 hours of Notebook GPU usage."

The Chinese version names 魔搭社区 (the ModelScope community). Neither version says which ModelScope site to use, which repo type counts, or what "the requirements" are.

## 1. Check first

Ask in the official Discord (https://discord.gg/2fS3a5YACg):

- **Which site counts:** modelscope.cn (魔搭社区) or modelscope.ai (international). Accounts and tokens may differ between the two.
- **Which repo type counts:** a Model repo, a Dataset repo, or a Studio (an app page).
- **What it must contain:** source, the build, the assets, the video? And when does verification happen?
- **Where the 20 GPU hours land:** which account, and on which site.

## 2. Prepare the folder

**Include** (adjust once you have the answers above):

- `README.md`, which becomes the model card. Put in it the pitch (the three lines from report slide 2), the video link, 3–4 in-engine stills, how to run the build, and the credits and licenses.
- `lux3d/`: the Lux3D GLB and PLY files that ship, the prompt table and the task IDs. First check whether Lux3D's terms allow redistributing generated assets.
- `tools/`: `Tools/Lux3D`, `Tools/Textures`, `Tools/Unreal` and `Tools/Splats`.
- Optionally, the packaged build zip (under 1 GB), so the page doubles as the demo download.

**Leave out:**

- **Secrets.** The Lux3D key (`LUX3D_API_KEY` or `~/.foa/lux3d_api_key`). Before uploading, grep the folder for `Authorization` and `api_key`.
- **Internal infrastructure:**
  - `JOINING.md`
  - the repo and server lines in `README.md` (tailnet URLs)
  - `.mcp.json`
  - the Multi-User and UdpMessaging lines in `Config/DefaultEngine.ini`, which point at the team's private Multi-User server
- **Generated folders:** `Saved/`, `Intermediate/`, `DerivedDataCache/` and `.playwright-mcp/`.

**Licensing:**

- The hackathon FAQ says all third-party content must be "properly licensed".
- Check the Unreal Engine EULA before you publish Epic's template content (`Content/Characters`, `Content/ThirdPerson`, `Content/LevelPrototyping`) in a public repo. If you're unsure, leave the UE project out and publish the tools, the assets and the build.
- The Poly Haven assets are CC0, so they can go in. Credit them anyway.

## 3. Upload a Model repo with the CLI

These steps follow https://www.modelscope.ai/docs/models/upload, read on Nov 5.

1. Register and log in on the site you confirmed. Create an access token under Account Settings → Access Tokens. The docs link to https://modelscope.ai/my/myaccesstoken.
2. Install the CLI with `pip install modelscope`.
3. Upload. If the repo doesn't exist, this command creates it, and new repos are public by default.

   ```
   modelscope upload <owner>/FoA-Nightmare-of-Responsibility <local folder> --repo-type model --token <TOKEN> --endpoint https://www.modelscope.ai
   ```

   - `--endpoint https://www.modelscope.ai` targets the international site, as in the docs example. Check which site the CLI uses when you leave the flag out.
   - `--repo-type dataset` makes a Dataset repo instead.
   - `--exclude '<glob>'` skips files.
   - Limits from the docs: files over 5 MB (and every `.zip`) go to LFS automatically, non-LFS files may total at most 500 MB, a single file can be up to 50 GB, and a repo can hold up to 100,000 files.
   - Keep the token in an environment variable rather than in any file.
4. Check the license and visibility on the repo's settings page on the site.
5. Open the repo page while logged out. Confirm that the README renders, the files are present and the links work.
6. Submit the repo URL in "My Submission" on the hackathon site, then screenshot the confirmation (capture S01).

## Studio alternative

ModelScope Studios support Gradio, Streamlit and a Static HTML SDK (https://www.modelscope.ai/docs/studios/intro), so a static project page with the video, stills and a download link is possible. The steps for creating a Studio haven't been verified. Follow the Studios docs if the organizers want one.

## When

Publish by Nov 17, so any verification problems show up before the Nov 19 06:00 EST deadline.
