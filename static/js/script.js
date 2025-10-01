// Seleciona todos os elementos que queremos aumentar
const elementos = document.querySelectorAll('h1, h2, h3, h4, h5, p, .btn');

// Guarda os tamanhos originais de cada elemento
elementos.forEach(el => {
    el.dataset.tamanhoOriginal = window.getComputedStyle(el).fontSize;
});

function aumentarTextosMobile() {
    if(window.innerWidth <= 480){ // celular
        elementos.forEach(el => {
            let tamanhoOriginal = parseFloat(el.dataset.tamanhoOriginal);
            el.style.fontSize = (tamanhoOriginal * 1.2) + 'px'; // aumenta 20% a partir do original
            el.style.fontWeight = '600'; // mais robusto
        });
    } else {
        // volta ao tamanho original se não for celular
        elementos.forEach(el => {
            el.style.fontSize = el.dataset.tamanhoOriginal;
            el.style.fontWeight = '';
        });
    }
}

// Executa ao carregar a página
window.addEventListener('load', aumentarTextosMobile);

// Executa ao redimensionar a tela
window.addEventListener('resize', aumentarTextosMobile);
