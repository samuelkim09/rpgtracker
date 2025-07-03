const socket = io();

socket.on("items_updated", () => location.reload());

document.getElementById("itemForm").onsubmit = async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = Object.fromEntries(new FormData(form).entries());

  data.value_or = parseInt(data.value_or) || 0;
  data.effect_value = parseInt(data.effect_value) || 0;
  data.in_shop = form.in_shop.checked;

  const res = await fetch("/create_item", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data)
  });

  if (res.ok) {
    alert("Objet créé !");
    form.reset();
  } else {
    alert("Erreur lors de la création.");
  }
};

function toggleShop() {
  fetch("/toggle_shop");
}
