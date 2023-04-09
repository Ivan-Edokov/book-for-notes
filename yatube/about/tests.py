from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse


class StaticUrlsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_url_pablic(self):
        """Страницы доступны любому пользователю"""
        url_names = {
            '/about/author/',
            '/about/tech/',
        }
        for adress in url_names:
            with self.subTest(adress=adress):
                response = self.client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """Url адрес использует правильные шаблоны"""
        template_urls_name = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
            reverse('about:author'): 'about/author.html',
            reverse('about:tech'): 'about/tech.html',
        }
        for adress, template in template_urls_name.items():
            with self.subTest(adress=adress):
                response = self.client.get(adress)
                self.assertTemplateUsed(response, template)
