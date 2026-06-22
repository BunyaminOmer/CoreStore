import os
import django
from django.utils.text import slugify

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'corelogic.settings')
django.setup()

from store.models import Category

category_tree = {
    'Elektronik': ['Bilgisayar', 'Akıllı Telefon', 'Tablet', 'Televizyon'],
    'Moda': ['Kadın Giyim', 'Erkek Giyim', 'Ayakkabı', 'Çanta & Aksesuar'],
    'Ev & Yaşam': ['Mobilya', 'Ev Dekorasyonu', 'Mutfak Eşyaları', 'Aydınlatma'],
    'Kozmetik & Kişisel Bakım': ['Parfüm', 'Cilt Bakımı', 'Makyaj', 'Saç Bakımı'],
    'Spor & Outdoor': ['Spor Giyim', 'Fitness Ekipmanları', 'Kamp Malzemeleri'],
    'Otomotiv & Motosiklet': ['Oto Aksesuar', 'Yedek Parça', 'Motosiklet Ekipmanları'],
}

def populate():
    for parent_name, children in category_tree.items():
        parent_slug = slugify(parent_name.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ö', 'o').replace('ü', 'u').replace('ğ', 'g'))
        parent, created = Category.objects.get_or_create(
            name=parent_name,
            defaults={'slug': parent_slug}
        )
        for child_name in children:
            child_slug = slugify(child_name.replace('ı', 'i').replace('ş', 's').replace('ç', 'c').replace('ö', 'o').replace('ü', 'u').replace('ğ', 'g'))
            Category.objects.get_or_create(
                name=child_name,
                parent=parent,
                defaults={'slug': f"{parent_slug}-{child_slug}"}
            )
    print("Kategoriler başarıyla oluşturuldu.")

if __name__ == '__main__':
    populate()
