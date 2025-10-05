# Lizard Bot v1.0 Release Notes

## 🎉 First Official Release!

Lizard Bot v1.0 is now available as a standalone Windows executable! This release marks the transition from a development project to a distributable application.

## 📦 What's New

### Executable Build System
- **Standalone Executable**: No Python installation required
- **All Dependencies Bundled**: Everything needed is included in the executable
- **Easy Distribution**: Single folder with all necessary files

### Build Tools
- `build_lizard.bat` - Builds the executable from source
- `create_distribution.bat` - Creates a distribution package
- `build_release.bat` - Complete build and distribution process
- `lizard_bot.spec` - PyInstaller configuration

## 🚀 Installation & Usage

### For End Users
1. Download the `LizardBot_v1.0` folder
2. Copy `.env.example` to `.env`
3. Edit `.env` and add your Discord bot token
4. Run `LizardBot.exe` or use `Start_LizardBot.bat`

### For Developers
1. Run `build_release.bat` to create a complete distribution
2. Or use individual scripts for specific build steps

## 📁 Distribution Contents

- `LizardBot.exe` - Main executable (3.2GB - includes all ML dependencies)
- `config.ini` - Bot configuration file
- `guild_configs.json` - Guild-specific settings
- `.env.example` - Environment variables template
- `README.txt` - User instructions
- `Start_LizardBot.bat` - Convenient launcher script

## 🔧 Technical Details

### Build System
- **PyInstaller 6.15.0** - Python to executable conversion
- **Single File Executable** - All dependencies bundled
- **Console Application** - Shows startup messages and errors
- **Asset Bundling** - All audio, images, and config files included

### Dependencies Included
- Discord.py with voice support
- Sentence Transformers (ML models)
- PyTorch and related libraries
- All required system libraries

### File Size
- **Executable**: ~3.2GB (includes ML models and dependencies)
- **Distribution**: ~3.2GB total

## 🎯 Features

All existing features are preserved:
- Random voice channel visits
- User kidnapping with dice rolls
- Guild-specific configurations
- Customizable settings
- AFK channel management
- Admin commands

## 🐛 Known Issues

- Large file size due to ML dependencies
- First startup may be slower (loading ML models)
- Windows Defender may flag as suspicious (false positive)

## 🔮 Future Improvements

- Optimize file size
- Add installer/updater
- Cross-platform builds (Linux/macOS)
- Code signing for Windows Defender

## 📞 Support

- GitHub: https://github.com/dragonjt2/Lizard
- Ko-fi: ko-fi.com/dragnai

---

**Build Date**: January 5, 2025  
**Version**: 1.0.0  
**Platform**: Windows 10/11 (64-bit)
