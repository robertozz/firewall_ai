# Makefile per gestione agente firewall AI

run:
	@echo "▶️ Avvio agente firewall..."
	python3 firewall_ai.py

test-telegram:
	@echo "📡 Test notifica Telegram..."
	python3 test_notify.py --html

html:
	@echo "🧾 Conversione log in HTML..."
	python3 utils/telegram_utils.py --html

clean:
	@echo "🧹 Pulizia log e HTML..."
	rm -f logs/firewall.log logs/firewall.html

flush:
	@echo "🧹 Flush e riapplicazione regole..."
	sudo python3 firewall_ai.py --flush

dry-run:
	@echo "🔎 Simulazione regole firewall..."
	sudo python3 firewall_ai.py --dry-run
