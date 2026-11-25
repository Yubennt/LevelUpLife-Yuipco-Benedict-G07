from django.shortcuts import render

# Create your views here.
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import Habit, HabitLog
from gamification.models import Level
from .forms import HabitForm

@login_required
def habit_list(request):
    habits = Habit.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'habits/habit_list.html', {'habits': habits})

@login_required
def habit_create(request):
    if request.method == 'POST':
        form = HabitForm(request.POST, user=request.user)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            form.save_m2m()

            # Create default streak record attached to user and habit
            HabitStreak.objects.get_or_create(
                habit=habit,
                user=request.user,
                defaults={'current_streak': 0, 'longest_streak': 0}
            )

            messages.success(request, f"Habit '{habit.title}' created successfully!")
            return redirect('habits:habit_list')
    else:
        form = HabitForm(user=request.user)

    return render(request, 'habits/habit_form.html', {'form': form, 'title': 'Create Habit'})
@login_required
def habit_update(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user, deleted_at__isnull=True)
    if request.method == 'POST':
        form = HabitForm(request.POST, instance=habit, user=request.user)
        if form.is_valid():
            habit = form.save()
            habit.tags.clear()
            raw_tags = form.cleaned_data.get('tag_names', '')
            tag_names = [t.strip() for t in raw_tags.split(',') if t.strip()]
            for name in tag_names:
                tag, _ = Tag.objects.get_or_create(user=request.user, name=name)
                habit.tags.add(tag)
            messages.success(request, f"Habit '{habit.title}' updated successfully!")
            return redirect('habits:habit_list')
    else:
        form = HabitForm(instance=habit, user=request.user)
    return render(request, 'habits/habit_form.html', {'form': form, 'title': 'Edit Habit'})

@login_required
def habit_delete(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user, deleted_at__isnull=True)
    if request.method == 'POST':
        habit.soft_delete()
        messages.success(request, f"Habit '{habit.title}' deleted.")
        return redirect('habits:habit_list')
    return render(request, 'habits/habit_confirm_delete.html', {'habit': habit})

@login_required
@require_POST
def toggle_habit_complete(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user, is_active=True, deleted_at__isnull=True)
    today = timezone.now().date()
    
    existing_log = HabitLog.objects.filter(habit=habit, completed_date=today).first()
    
    if existing_log:
        xp_to_remove = existing_log.xp_earned
        existing_log.delete()
        
        request.user.total_xp = max(0, request.user.total_xp - xp_to_remove)
        
        # Recalculate level on XP loss
        current_lvl = Level.objects.filter(xp_required__lte=request.user.total_xp).order_by('-level_number').first()
        if current_lvl and request.user.current_level != current_lvl:
            request.user.current_level = current_lvl
            
        request.user.save()
        messages.info(request, f"Unchecked '{habit.title}'. ({xp_to_remove} XP removed)")
    else:
        xp_earned = habit.xp_reward
        HabitLog.objects.create(
            habit=habit,
            user=request.user,
            completed_date=today,
            xp_earned=xp_earned
        )
        
        old_level = request.user.current_level
        request.user.total_xp += xp_earned
        
        # Check for level up
        new_level = Level.objects.filter(xp_required__lte=request.user.total_xp).order_by('-level_number').first()
        if new_level and new_level != old_level:
            request.user.current_level = new_level
            messages.success(request, f"🎉 LEVEL UP! You reached Level {new_level.level_number}: {new_level.title}!")
            
        request.user.save()
        messages.success(request, f"Completed '{habit.title}'! +{xp_earned} XP earned!")
        
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))