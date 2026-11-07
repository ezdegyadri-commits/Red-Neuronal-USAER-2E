import re

with open('piloto_spa/backend/static/index.html', encoding='utf-8') as f:
    text = f.read()

start = text.find('<script type="text/babel">')
end = text.rfind('</script>')
code = text[start:end]

stack = []
errors = []
in_str = None
in_comment = False
for line_no, line in enumerate(code.splitlines(), start=1):
    i = 0
    while i < len(line):
        ch = line[i]
        if in_comment:
            if ch == '*' and i + 1 < len(line) and line[i+1] == '/':
                in_comment = False
                i += 1
        elif in_str:
            if ch == '\\':
                i += 1
            elif ch == in_str:
                in_str = None
        else:
            if ch == '/' and i + 1 < len(line) and line[i+1] == '/':
                break
            elif ch == '/' and i + 1 < len(line) and line[i+1] == '*':
                in_comment = True
                i += 1
            elif ch in ('"', "'", '`'):
                in_str = ch
            elif ch in '{[(':
                stack.append((ch, line_no))
            elif ch in '}])':
                if not stack:
                    errors.append(f"Extra {ch} at line {line_no}")
                else:
                    open_ch, open_line = stack.pop()
                    expected = {'{': '}', '[': ']', '(': ')'}[open_ch]
                    if ch != expected:
                        errors.append(f"Mismatched {open_ch} (line {open_line}) with {ch} (line {line_no})")
        i += 1

print(f"Errors: {len(errors)}")
for e in errors[:10]:
    print(e)
print(f"Remaining unclosed: {len(stack)}")
for s in stack[:10]:
    print(s)
