# Android dev APK

Issue: #1305

The **Android dev APK** workflow packages the ordinary Second Gate Project through the canonical Thestra `.love` export and then embeds that archive into the pinned official `love2d/love-android` wrapper.

The intended owner workflow is:

```text
GitHub -> Actions -> Android dev APK -> Run workflow -> download artifact -> install/update -> play
```

No local Android Studio or developer computer is required for ordinary builds.

## What is pinned

The workflow currently uses:

- desktop/export runtime: the repository's pinned LÖVE 11.5 action;
- Android wrapper: `love2d/love-android` 11.5a commit `55feb38fa144f4734c26742389f279fb07d955c0`;
- Android API: 34;
- NDK: `25.2.9519653`;
- build tools: `34.0.0`;
- Java: 17.

11.5a is intentional: it is the Android hotfix release that repaired embedded-game loading and save-directory regressions in the original 11.5 Android release.

## One app, repeated updates

The dev application id is `io.github.josephserusp.hichaukitoden.dev`; display
names remain Project-authored. APKs from the pre-integration experimental
`secondgate.dev` id are a different Android application and do not update into
this package or share its Android save directory.

Android registers its device surface even with the virtual gamepad hidden and
preserves an explicit ASPECT preference across launches. Narrow landscape
devices reserve complete side controls before fitting the surface; portrait
devices reserve a lower control band. Desktop dock geometry remains authored.

Project Android identity lives in `projects/hichaukitoden-game/data/project.json`.
The dev workflow derives a separate development package id by appending `.dev` and appends `Dev` to the display name. That keeps the eventual release identity available for a production app while repeated development builds target one installed dev application.

`versionCode` is generated from UTC epoch seconds at build time. This is monotonically increasing for normal CI use and remains below Android's 2.1-billion ceiling until 2036; the workflow fails loudly after that instead of wrapping silently.

## Stable signing for update-in-place

For true update-in-place builds, configure the repository Actions secret:

```text
ANDROID_DEV_DEBUG_KEYSTORE_BASE64
```

It must contain the base64 representation of a persistent Java keystore using:

```text
alias:      androiddebugkey
storepass:  android
keypass:    android
```

A compatible one-time key can be created with:

```bash
keytool -genkeypair -noprompt \
  -keystore hichaukitoden-dev.keystore \
  -storepass android \
  -alias androiddebugkey \
  -keypass android \
  -dname "CN=Second Gate Dev,O=Thestra,C=BR" \
  -keyalg RSA -keysize 2048 -validity 10000
```

Then base64-encode the file as one line and store that text as the secret. Keep the original keystore backed up outside the repository as well. Do **not** commit the keystore or print its base64 value into a workflow log.

If the secret is absent, the workflow deliberately creates an **ephemeral** signing key for that run. The resulting APK is installable and useful for first-device smoke testing, but the next CI run will have a different certificate and Android will require uninstalling the previous ephemeral build first. The workflow and job summary warn when this fallback is active; it does not satisfy #1305's update-in-place acceptance criterion.

## Artifact

A successful manual run uploads `hichaukitoden-dev.apk` plus small provenance files for 14 days. The workflow verifies package id, version code/name, APK signature, and the embedded canonical `.love` SHA-256 after signing before publishing the artifact.

The current lane intentionally does not include Android Effekseer. Missing native effects remain the known graceful-degradation case until the native integration audit and Android renderer work are separately scoped.
