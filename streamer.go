package main

import (
	"bytes"
	"compress/zlib"
	"database/sql"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type Animation struct {
	Slug   string   `json:"slug"`
	Title  string   `json:"title"`
	FPS    int      `json:"fps"`
	Width  int      `json:"width"`
	Frames []string `json:"frames"`
}

var (
	db       *sql.DB
	cache    = make(map[string]*Animation)
	cacheMux sync.RWMutex
)

func decompressFrames(compressed []byte) ([]string, error) {
	r, err := zlib.NewReader(bytes.NewReader(compressed))
	if err != nil {
		return nil, err
	}
	defer r.Close()

	var buf bytes.Buffer
	if _, err := io.Copy(&buf, r); err != nil {
		return nil, err
	}

	frames := strings.Split(buf.String(), "\n---FRAME---\n")
	return frames, nil
}

func getAnimation(slug string) (*Animation, error) {
	slug = strings.ToLower(strings.Trim(slug, "/"))

	cacheMux.RLock()
	if anim, ok := cache[slug]; ok {
		cacheMux.RUnlock()
		return anim, nil
	}
	cacheMux.RUnlock()

	var title string
	var fps, width int
	var blob []byte

	err := db.QueryRow("SELECT title, fps, width, frames_blob FROM animations WHERE slug = ?", slug).Scan(&title, &fps, &width, &blob)
	if err != nil {
		return nil, err
	}

	frames, err := decompressFrames(blob)
	if err != nil {
		return nil, err
	}

	anim := &Animation{
		Slug:   slug,
		Title:  title,
		FPS:    fps,
		Width:  width,
		Frames: frames,
	}

	cacheMux.Lock()
	cache[slug] = anim
	cacheMux.Unlock()

	return anim, nil
}

func streamHandler(w http.ResponseWriter, r *http.Request) {
	slug := strings.TrimPrefix(r.URL.Path, "/")
	if slug == "" {
		http.Redirect(w, r, "/health", http.StatusFound)
		return
	}

	anim, err := getAnimation(slug)
	if err != nil {
		http.Error(w, fmt.Sprintf("Animation '%s' not found.\n", slug), http.StatusNotFound)
		return
	}

	ua := strings.ToLower(r.Header.Get("User-Agent"))
	isCurl := strings.Contains(ua, "curl") || strings.Contains(ua, "wget") || r.URL.Query().Get("raw") == "1"

	if !isCurl {
		http.Redirect(w, r, fmt.Sprintf("/viewer?slug=%s", slug), http.StatusFound)
		return
	}

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.Header().Set("Transfer-Encoding", "chunked")
	w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate, no-transform")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)

	// Async view counter increment
	go func() {
		_, _ = db.Exec("UPDATE animations SET views = views + 1 WHERE slug = ?", slug)
	}()

	delay := time.Duration(1000/anim.FPS) * time.Millisecond
	ctx := r.Context()
	idx := 0

	for {
		select {
		case <-ctx.Done():
			return
		default:
			fmt.Fprint(w, anim.Frames[idx])
			flusher.Flush()
			time.Sleep(delay)
			idx = (idx + 1) % len(anim.Frames)
		}
	}
}

func main() {
	port := flag.String("port", "8080", "Server port")
	dbPath := flag.String("db", os.TempDir()+"/ascii_live_database.db", "SQLite DB path")
	flag.Parse()

	var err error
	db, err = sql.Open("sqlite3", *dbPath+"?_journal_mode=WAL")
	if err != nil {
		log.Fatalf("Failed to open DB: %v", err)
	}
	defer db.Close()

	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "healthy", "engine": "go-streamer"})
	})
	http.HandleFunc("/", streamHandler)

	log.Printf("[GO STREAMER] Listening on :%s (Connected to %s)", *port, *dbPath)
	if err := http.ListenAndServe(":"+*port, nil); err != nil {
		log.Fatal(err)
	}
}

