from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username="author")
        cls.not_author = User.objects.create_user(
            username='not_author'
        )

        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
        )

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testslug',
            description='Тестовое описание',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(StaticURLTests.author)
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(
            StaticURLTests.not_author
        )

    def test_url_public(self):
        """Страницы доступны любому пользователю."""
        url_names = {
            "/",
            f"/group/{self.group.slug}/",
            f"/profile/{StaticURLTests.author}/",
            f"/posts/{self.post.id}/",
        }
        for adress in url_names:
            with self.subTest(adress=adress):
                response = self.client.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_authorized_not_author(self):
        """
        Страницы доступны только авторезированному пользователю.
        """
        url_names = {
            "/",
            f"/group/{self.group.slug}/",
            f"/profile/{StaticURLTests.not_author}/",
            f"/posts/{self.post.id}/",
            "/create/",
        }
        for adress in url_names:
            with self.subTest(adress=adress):
                response = self.authorized_client_not_author.get(adress)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_authorized_author(self):
        """Страница редактирования поста доступна только автору поста."""
        response = self.authorized_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            "/": "posts/index.html",
            f"/group/{self.group.slug}/": "posts/group_list.html",
            f"/profile/{StaticURLTests.author}/": "posts/profile.html",
            f"/posts/{self.post.id}/": "posts/post_detail.html",
            f"/posts/{self.post.id}/edit/": "posts/create_post.html",
            "/create/": "posts/create_post.html",
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)

    def test_page_not_found(self):
        """Страница не найдена"""
        response = self.authorized_client.get("/unexisting_page/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
