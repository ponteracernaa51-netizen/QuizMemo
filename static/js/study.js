let cards = [];
let currentIndex = 0;
const deckId = document.getElementById('study-app').dataset.deck;

async function loadCards() {
    const res = await fetch(`/api/cards/${deckId}`);
    cards = await res.json();
    if (cards.length === 0) {
        document.getElementById('question').innerText = "Все карточки изучены на сегодня!";
    } else {
        renderCard();
    }
}

function renderCard() {
    const card = cards[currentIndex];
    document.getElementById('question').innerText = card.question_text;
    const optionsDiv = document.getElementById('options');
    optionsDiv.innerHTML = '';
    document.getElementById('feedback').style.display = 'none';

    card.options.forEach(opt => {
        const btn = document.createElement('button');
        btn.innerText = opt;
        btn.onclick = () => checkAnswer(opt, card.correct_answer);
        optionsDiv.appendChild(btn);
    });
}

function checkAnswer(selected, correct) {
    const resText = document.getElementById('result');
    document.getElementById('controls').style.display = 'block';
    
    if (selected == correct) {
        resText.innerText = "✅ Правильно!";
        resText.className = "res-correct";
    } else {
        resText.innerText = `❌ Ошибка! Правильный ответ: ${correct}`;
        resText.className = "res-wrong";
    }
    document.querySelectorAll('.option-btn').forEach(btn => btn.disabled = true);
}

async function handleRating(rating) {
    await fetch('/api/rate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            card_id: cards[currentIndex].id,
            rating: rating
        })
    });
    
    currentIndex++;
    if (currentIndex < cards.length) {
        renderCard();
    } else {
        alert("Сессия окончена!");
        window.location.href = '/dashboard';
    }
}

loadCards();