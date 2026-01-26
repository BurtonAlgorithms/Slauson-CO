# Setting Up Google Drive File: "Portfolio Slides.pdf"

## Your Setup

- **File name**: `Portfolio Slides.pdf`
- **Folder**: `Slauson Deck (Portco Slides)`

## How the Code Finds Files

The code uses `find_file_id_by_name()` which:
1. ✅ Searches for files by **exact name match** (case-sensitive)
2. ✅ Can search within a specific folder if `GOOGLE_DRIVE_FOLDER_ID` is set
3. ✅ Falls back to global search if not found in folder

## Configuration Required

You need to set **two environment variables**:

### Option 1: Use File Name + Folder ID (Recommended)

```bash
GOOGLE_DRIVE_STATIC_FILE_NAME=Portfolio Slides.pdf
GOOGLE_DRIVE_FOLDER_ID=<folder_id_of_Slauson_Deck_(Portco_Slides)>
```

### Option 2: Use Direct File ID (Easiest)

```bash
GOOGLE_DRIVE_STATIC_FILE_ID=<file_id_of_Portfolio_Slides.pdf>
```

## How to Get the Folder ID

1. Open Google Drive
2. Navigate to folder: `Slauson Deck (Portco Slides)`
3. Open the folder
4. Look at the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
5. Copy the `FOLDER_ID_HERE` part

## How to Get the File ID

1. Open Google Drive
2. Navigate to: `Slauson Deck (Portco Slides)` → `Portfolio Slides.pdf`
3. Right-click the file → "Get link" or open it
4. Look at the URL: `https://drive.google.com/file/d/FILE_ID_HERE/view`
5. Copy the `FILE_ID_HERE` part

## Setting in Render/Railway

Add these environment variables:

**Option 1 (Name + Folder):**
```
GOOGLE_DRIVE_STATIC_FILE_NAME=Portfolio Slides.pdf
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
```

**Option 2 (Direct File ID - Easiest):**
```
GOOGLE_DRIVE_STATIC_FILE_ID=your_file_id_here
```

## Important Notes

⚠️ **Case-Sensitive**: The file name must match **exactly** (including spaces and capitalization)
- ✅ `Portfolio Slides.pdf` 
- ❌ `portfolio slides.pdf`
- ❌ `PortfolioSlides.pdf`

⚠️ **Folder Search**: If you use `GOOGLE_DRIVE_FOLDER_ID`, the code will:
1. First search within that folder
2. If not found, fall back to global search

⚠️ **File ID is Best**: Using `GOOGLE_DRIVE_STATIC_FILE_ID` is the most reliable because:
- No name matching needed
- No folder search needed
- Direct file access

## Current Behavior

With your setup, the code will:
1. ✅ Look for `Portfolio Slides.pdf` by name
2. ✅ Search in `Slauson Deck (Portco Slides)` folder (if `GOOGLE_DRIVE_FOLDER_ID` is set)
3. ✅ Download the existing PDF
4. ✅ Append or replace the new slide
5. ✅ Upload the merged PDF back to the same file

## Testing

After setting the environment variables:
1. Run a test webhook
2. Check the logs - you should see:
   ```
   Found static Drive file by name 'Portfolio Slides.pdf': <file_id>
   ```
3. The file should be updated in place

## Troubleshooting

**"File not found"**
- Check that `GOOGLE_DRIVE_STATIC_FILE_NAME` matches exactly (case-sensitive)
- Verify `GOOGLE_DRIVE_FOLDER_ID` is correct
- Or use `GOOGLE_DRIVE_STATIC_FILE_ID` instead

**"Multiple files found"**
- The code uses the first match
- Use `GOOGLE_DRIVE_STATIC_FILE_ID` to be specific

**"Permission denied"**
- Make sure the OAuth account has access to the folder and file

