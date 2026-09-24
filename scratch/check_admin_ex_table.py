with open('templates/admin.html', 'r', encoding='utf-8') as f:
    text = f.read()

p1 = text.find('<table class="custom-table" id="exhibitorsTable">')
p2 = text.find('</table>', p1)
print("HTML Table Header:")
print(text[p1:p2+8])

p3 = text.find('async function loadExhibitors(')
p4 = text.find('function changeExhibitorPage', p3)
print("\nJS loadExhibitors:")
print(text[p3:p4])
