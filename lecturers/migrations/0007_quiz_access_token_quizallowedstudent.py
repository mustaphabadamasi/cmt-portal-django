import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def gen_unique_tokens(apps, schema_editor):
    Quiz = apps.get_model('lecturers', 'Quiz')
    for quiz in Quiz.objects.all():
        quiz.access_token = uuid.uuid4()
        quiz.save(update_fields=['access_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('lecturers', '0006_assignment_group_question_and_more'),
        ('students', '0001_initial'),
    ]

    operations = [
        # Step 1: add field WITHOUT unique constraint, nullable
        migrations.AddField(
            model_name='quiz',
            name='access_token',
            field=models.UUIDField(null=True, blank=True),
        ),
        # Step 2: populate unique values for existing rows
        migrations.RunPython(gen_unique_tokens, migrations.RunPython.noop),
        # Step 3: make it non-nullable and unique
        migrations.AlterField(
            model_name='quiz',
            name='access_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True, editable=False),
        ),
        # Step 4: add QuizAllowedStudent model
        migrations.CreateModel(
            name='QuizAllowedStudent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('added_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lecturers.lecturer')),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allowed_students', to='lecturers.quiz')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_access', to='students.student')),
            ],
            options={'unique_together': {('quiz', 'student')}},
        ),
    ]
