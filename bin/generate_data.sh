    #!/bin/bash

function generate_resource()
{
    echo '<?xml version="1.0" encoding="UTF-8"?>'
    echo '<gresources>'
    echo '  <gresource prefix="/org/scarlatti/Scarlatti">'
    for file in data/*.css
    do
        echo -n '    <file compressed="true">'
        echo -n $(basename $file)
        echo '</file>'
    done
    for file in data/*.ui AboutDialog.ui
    do
        echo -n '     <file compressed="true" preprocess="xml-stripblanks">'
        echo -n $(basename $file)
        echo '</file>'
    done
    echo '  </gresource>'
    echo '</gresources>'
}

function generate_po()
{
    cd po
    git pull https://github.com/krischerven/scarlatti-translations > scarlatti.pot
    for file in ../data/org.scarlatti.Scarlatti.gschema.xml ../data/*.in ../data/*.ui ../scarlatti/*.py
    do
        xgettext --from-code=UTF-8 -j $file -o scarlatti.pot
    done
    >LINGUAS
    for po in *.po
    do
        msgmerge -N $po scarlatti.pot > /tmp/$$language_new.po
        mv /tmp/$$language_new.po $po
        language=${po%.po}
        echo $language >>LINGUAS
    done
}

generate_resource > data/scarlatti.gresource.xml
generate_po
