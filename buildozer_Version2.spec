[app]
# (str) Title of your application
title = Space Dodger — Cat Attack

# (str) Package name (no spaces, all lowercase)
package.name = space_dodger

# (str) Package domain (reverse DNS). Change to your own domain if you have one.
package.domain = org.example

# (str) Source code location (relative)
source.dir = .

# (list) Patterns to include in the APK; include images, sounds, json, svgs
source.include_exts = py,pyc,png,jpg,jpeg,wav,ogg,svg,json,txt

# (str) Application versioning
version = 0.1

# (list) Application requirements: python-for-android provides a pygame recipe.
requirements = python3,pygame

# (str) Which architectures to build for. Building both increases build time.
android.arch = armeabi-v7a, arm64-v8a

# (int) Android API to target
android.api = 31

# (str) Android NDK version if you need to pin (optional)
# android.ndk = 23b

# (str) Permissions your app needs
android.permissions = INTERNET

# (int) Orientation: landscape recommended for this game
orientation = landscape

# (bool) Fullscreen
fullscreen = 0

[buildozer]
# directory in which to place build artifacts
build_dir = ./.buildozer

# (int) number of jobs for building (uncomment and tune for more cores)
# jobs = 2