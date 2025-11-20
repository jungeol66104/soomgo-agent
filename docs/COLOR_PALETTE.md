# Color Palette

**Used in CLI chat interface for consistent theming**

## Colors

| Name | RGB | Hex | Usage |
|------|-----|-----|-------|
| **Primary** | `rgb(105, 59, 242)` | `#693BF2` | Main purple - Agent label |
| **Primary Dim** | `rgb(130, 90, 255)` | `#825AFF` | Lighter purple - accents |
| **User** | `rgb(52, 211, 153)` | `#34D399` | Cyan/teal - You label |
| **User Text** | `rgb(209, 250, 229)` | `#D1FAE5` | Light mint - your messages |
| **Success** | `rgb(46, 213, 115)` | `#2ED573` | Green - success messages |
| **Warning** | `rgb(255, 159, 67)` | `#FF9F43` | Orange - warnings, reset |
| **Error** | `rgb(255, 71, 87)` | `#FF4757` | Red - error messages |
| **Text** | `rgb(245, 246, 250)` | `#F5F6FA` | Off-white - agent messages |
| **Text Dim** | `rgb(160, 170, 185)` | `#A0AAB9` | Gray - secondary text |
| **Background** | `rgb(30, 32, 38)` | `#1E2026` | Dark - background |

## Visual Preview

```
Soomgo Agent v0                            ← Primary
Interactive CLI Chat Interface             ← Text Dim

Commands: /reset /quit /help               ← Text Dim
Input: Enter to send • Shift+Enter...      ← Text Dim

✓ Agent ready!                             ← Success

You                                        ← User (cyan/teal)
> Type your message here
Your message displayed here                ← User Text (light mint)

Agent                                      ← Primary (purple)
Agent response here                        ← Text (off-white)

You                                        ← User
> Another message
Another message displayed                  ← User Text

Agent                                      ← Primary
Another response                           ← Text

Commands in /help                          ← User (cyan for commands)
✓ Conversation reset                       ← Warning
✗ Error message                            ← Error
```

## Usage in Code

```python
# Import in cli/chat.py
COLORS = {
    "primary": "rgb(105,59,242)",      # Agent label
    "primary_dim": "rgb(130,90,255)",  # Lighter purple
    "user": "rgb(52,211,153)",         # You label
    "user_text": "rgb(209,250,229)",   # Your messages
    "success": "rgb(46,213,115)",      # Green
    "warning": "rgb(255,159,67)",      # Orange
    "error": "rgb(255,71,87)",         # Red
    "text": "rgb(245,246,250)",        # Agent messages
    "text_dim": "rgb(160,170,185)",    # Gray
    "bg": "rgb(30,32,38)",             # Dark bg
}

# Use in Rich formatting
console.print(f"[bold {COLORS['user']}]You[/bold {COLORS['user']}]")
console.print(f"[{COLORS['user_text']}]Your message[/{COLORS['user_text']}]")
console.print(f"[bold {COLORS['primary']}]Agent[/bold {COLORS['primary']}]")
console.print(f"[{COLORS['text']}]Agent response[/{COLORS['text']}]")
```

## Accessibility

- Primary purple has sufficient contrast against dark backgrounds
- Text colors meet WCAG AA standards for readability
- Success/Warning/Error colors are distinguishable for color-blind users

---

**Last Updated**: 2025-11-05
