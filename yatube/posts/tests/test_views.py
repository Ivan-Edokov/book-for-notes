import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)

TEST_TOTAL_POSTS = 13
SECOND_PAGE = 3


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="author")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="testslug",
            description="Тестовое описание",
        )
        uploaded = SimpleUploadedFile(
            name='small_gif',
            content=SMALL_GIF,
            content_type="image/gif",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовый пост",
            group=cls.group,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.autoriset_client = Client()
        self.autoriset_client.force_login(PostPagesTests.user)

    def comparison_data_context_database(self, obj_context, db_obj):
        """
        Проверка объекта контекста с объектом БД,
        по полям id, text, author, group
        """
        self.assertEqual(obj_context.id, db_obj.id)
        self.assertEqual(obj_context.text, db_obj.text)
        self.assertEqual(obj_context.author, db_obj.author)
        self.assertEqual(obj_context.group, db_obj.group)
        self.assertEqual(obj_context.image, db_obj.image)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.user}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.autoriset_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index, список постов сформирован с правильным контекстом."""
        response = self.autoriset_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        db_obj = Post.objects.first()
        self.comparison_data_context_database(first_object, db_obj)

    def test_group_list_pages_show_correct_context(self):
        """Шаблон group_list список постов, отфильтрованных по группе."""
        response = self.autoriset_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        first_object = response.context['page_obj'][0]
        db_obj = Post.objects.filter(group=self.group).first()
        self.comparison_data_context_database(first_object, db_obj)

    def test_profile_pages_show_correct_context(self):
        """Шаблон profile список постов, отфильтрованных по автору."""
        response = self.autoriset_client.get(
            reverse('posts:profile', kwargs={'username': self.user})
        )
        first_object = response.context['page_obj'][0]
        db_obj = Post.objects.filter(author=self.user).first()
        self.comparison_data_context_database(first_object, db_obj)

    def test_post_detail_show_correct_context(self):
        """
        Шаблон post_detail подробное описание поста
        отфильтрованного по id.
         """
        response = self.autoriset_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.context['post'].text, self.post.text)
        self.assertEqual(response.context['post'].author, self.user)
        self.assertEqual(response.context['post'].group, self.group)
        self.assertEqual(response.context['post'].image, self.post.image)

    def test_post_create_pages_show_correct_context(self):
        """
        Шаблон post_create добавление поста сформирован
        с правильным контекстом.
        """
        response = self.autoriset_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_pages_show_correct_context(self):
        """
        Шаблон post_edit редактирование поста сформирован
        с правильным контекстом.
        """
        response = self.autoriset_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_new_post_on_index(self):
        """При создании и заполнении группы текст добавлен корректно"""
        response_index = self.autoriset_client.get(reverse('posts:index'))
        response_group = self.autoriset_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        response_profile = self.autoriset_client.get(
            reverse('posts:profile', kwargs={'username': self.user})
        )
        index = response_index.context['page_obj']
        group = response_group.context['page_obj']
        profile = response_profile.context['page_obj']
        self.assertIn(self.post, index)
        self.assertIn(self.post, group)
        self.assertIn(self.post, profile)

    def test_post_is_not_in_another_group(self):
        '''Пост не попал в группу, для которой не был предназначен.'''
        second_group = Group.objects.create(
            title='Вторая тестовая группа',
            slug='testslug_2',
            description='Описание второй группы',
        )
        response = self.autoriset_client.get(
            reverse('posts:group_list', kwargs={'slug': second_group.slug})
        )
        self.assertNotIn(PostPagesTests.post, response.context['page_obj'])

    def test_comment_app_on_post_page(self):
        """После успешной отправки комментарий появляется на странице поста"""
        comment_text = 'Новый добавленный комментарий к посту'
        form_data = {'text': comment_text}
        response = self.autoriset_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostPagesTests.post.id}
            ),
            data=form_data,
            follow=True,
        )
        response = self.client.post(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostPagesTests.post.id})
        )
        comment_obj = response.context["comments"][0]
        self.assertEqual(comment_obj.author, PostPagesTests.user)
        self.assertEqual(comment_obj.text, comment_text)

    def test_cache_render_page_index(self):
        """На index.html данные кешируются корректно"""
        response = self.client.get(reverse('posts:index'))
        cache_content_index = response.content
        uploaded = SimpleUploadedFile(
            name='small_gif',
            content=SMALL_GIF,
            content_type="image/gif",
        )
        self.post = Post.objects.create(
            text='2 пост',
            author=PostPagesTests.user,
            group=self.group,
            image=uploaded
        )
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(response.content, cache_content_index)
        cache.clear()
        response = self.client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, cache_content_index)


class PaginatorViewsTest(TestCase):
    '''Класс Paginator проверка количества постов на странице'''
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author_2')
        cls.group_p = Group.objects.create(
            title="Тестовая группа Pag",
            slug="testslug_pag",
            description="Тестовое описание pag",
        )

        obj_post_pagin = (
            Post(
                author=cls.user,
                text='Тестовый пост Pag',
                group=cls.group_p,
            )
            for i in range(TEST_TOTAL_POSTS)
        )
        Post.objects.bulk_create(obj_post_pagin)

    def setUp(self):
        self.autoriset_user = Client()
        self.autoriset_user.force_login(PaginatorViewsTest.user)

    def comparison_sum_posts_1_and_2_pages(self, page_1, page_2):
        """
        Сравнение количества записей на первой и второй странице
        с заданным значением Paginator
        """
        self.assertEqual(
            len(page_1.context['page_obj']), settings.LIMIT_POST
        )
        self.assertEqual(len(page_2.context['page_obj']), SECOND_PAGE)

    def test_index_page_contains_ten_records(self):
        '''Шаблон index проверка колчества постов'''
        response = self.autoriset_user.get(reverse('posts:index'))
        response_2 = self.autoriset_user.get(reverse(
            'posts:index') + '?page=2')
        self.comparison_sum_posts_1_and_2_pages(response, response_2)

    def test_group_list_page_contains_ten_records(self):
        '''Шаблон group_list проверка колчества постов'''
        response = self.autoriset_user.get(reverse(
            'posts:group_list', kwargs={'slug': self.group_p.slug})
        )
        response_2 = self.autoriset_user.get(reverse(
            'posts:group_list', kwargs={'slug': self.group_p.slug})
            + '?page=2'
        )
        self.comparison_sum_posts_1_and_2_pages(response, response_2)

    def test_profile_page_contains_ten_records(self):
        '''Шаблон profile проверка колчества постов'''
        response = self.autoriset_user.get(reverse(
            'posts:profile', kwargs={'username': PaginatorViewsTest.user})
        )
        response_2 = self.autoriset_user.get(reverse(
            'posts:profile', kwargs={'username': PaginatorViewsTest.user})
            + '?page=2'
        )
        self.comparison_sum_posts_1_and_2_pages(response, response_2)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.follower = User.objects.create_user(username='follower')
        cls.post = Post.objects.create(
            text='Текст тестового поста',
            author=cls.author,
        )

    def setUp(self):
        self.follower = Client()
        self.follower.force_login(FollowViewsTest.follower)
        self.author = Client()
        self.author.force_login(FollowViewsTest.author)

    def test_authorized_user_can_follow(self):
        """Авторизованный пользователь может подписаться """
        self.follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': FollowViewsTest.author}
        ))
        self.assertTrue(Follow.objects.filter(
            user=FollowViewsTest.follower,
            author=FollowViewsTest.author
        ).exists())

    def test_authorized_user_can_unfollow(self):
        """Авторизованный пользователь может отписаться от автора поста"""
        self.follower.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': FollowViewsTest.author}
        ))
        self.assertFalse(Follow.objects.filter(
            user=FollowViewsTest.follower,
            author=FollowViewsTest.author
        ).exists())

    def test_new_post_on_follower_and_unfollower_page(self):
        """
        Новая запись автора появляется на страницах подписчиков
        и не появляется на странице пользователя не подписанного
        на автора.
        """
        form_data = {
            'text': 'Текст второго тестового поста'
        }
        response = self.author.post(reverse(
            'posts:post_create'),
            data=form_data,
            follow=True
        )
        new_post = response.context['page_obj'][0]
        self.follower.get(reverse(
            'posts:profile_follow',
            kwargs={'username': FollowViewsTest.author}
        ))
        response = self.follower.get(reverse(
            'posts:follow_index'
        ))
        self.assertEqual(new_post.id, response.context['page_obj'][0].id)
        self.follower.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': FollowViewsTest.author}
        ))
        response = self.follower.get(reverse(
            'posts:follow_index'
        ))
        self.assertNotIn(
            new_post.text, response.context['page_obj'].object_list
        )
