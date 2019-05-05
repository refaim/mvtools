import os
import pysubs2
import sys

if __name__ == '__main__':
    root = sys.argv[1]
    style = sys.argv[2]
    for name in sorted(os.listdir(root)):
        if name.endswith('.ass') or name.endswith('.ssa'):
            sub_file = pysubs2.load(os.path.join(root, name), encoding="utf-8")
            new_events = []
            for event in sub_file:
                if event.style == style and event.type == 'Dialogue' and event.text.strip() != '':
                    new_events.append(event)
            sub_file.events = new_events
            sub_file.save(os.path.join(root, os.path.splitext(name)[0] + '_2.ass'))
