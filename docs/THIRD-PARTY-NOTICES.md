# Third-party assets and packages

Custom application code is supplied under the MIT licence in the root `LICENSE`. This does not relicense third-party packages or fonts. Their own licence terms continue to apply.

Python packages and their exact versions are listed in `requirements.lock`. npm build-time packages and versions are listed in `package-lock.json`. `docs/licenses/python-packages.tsv` and `docs/licenses/npm-packages.tsv` record licence metadata from the installed locked distributions. Available distribution licence/notice files are copied into the adjacent `python/` and `npm/` directories. Distribution metadata may omit a licence classifier; consult that package's bundled licence/source before redistribution when it is unspecified.

Principal runtime components include Django (BSD), django-two-factor-auth (MIT), django-otp (BSD), django-axes (MIT), Psycopg (LGPL, including its binary redistribution terms), Pillow (HPND-style licence), WhiteNoise (MIT), Gunicorn (MIT), python-dotenv (BSD), dj-database-url (BSD), Argon2 bindings (MIT) and their pinned dependencies. The copied package notices, rather than this short summary, are authoritative.

Tailwind CSS and its build dependencies are build-time packages. Self-hosted **Manrope** and **Cormorant Garamond** font files are distributed under the SIL Open Font License; full OFL notices are included as `Manrope-OFL.txt` and `Cormorant-Garamond-OFL.txt`. Fontsource's packaging metadata is also included in the npm notices. No Google Fonts CDN request or paid font account is needed.

The SVG icons, fallback Kairos wordmark/monogram, clock animation and placeholder illustration are original project assets. A supplied business logo would remain subject to the business owner's rights; no actual user logo was provided.

Seven watch photographs were generated for this project using the built-in image-generation tool: one cinematic hero and six catalogue concepts. No stock-photo site, existing watch brand, named commercial model, copied logo or real authenticity claim was used in the prompts. These are explicitly demonstration images, not evidence that a real watch exists or has any particular specifications. They must be replaced or verified for actual inventory. See `ASSETS.md` for paths and prompt briefs. Generated outputs do not establish trademark clearance or exclusive rights.

Docker's Python base image and PostgreSQL image carry their own upstream package notices. They are pulled by Docker and are not embedded inside this ZIP. Review their supported versions and security patches when deploying. No GSAP library, third-party analytics, payment SDK or external image CDN is included.

Primary references used during implementation:

- https://www.djangoproject.com/download/ (supported Django 5.2 LTS series)
- https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- https://django-two-factor-auth.readthedocs.io/en/stable/installation.html
- https://django-axes.readthedocs.io/
- https://www.postgresql.org/docs/17/backup-dump.html

Review dependencies for newer security patch releases before a production launch; the lockfiles reproduce this handover's tested package set rather than automatically changing installed versions.

Cloud media support adds django-storages (BSD-3-Clause), boto3/botocore/s3transfer (Apache-2.0), and their pinned dependencies. Their available notices are bundled in docs/licenses/python. Meta, Vercel, email and storage services have separate account terms and usage charges; their credentials and services are not embedded in this ZIP.
